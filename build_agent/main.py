# Copyright (2025) Bytedance Ltd. and/or its affiliates 

# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 


import argparse
import json
import multiprocessing
import threading
import time
import os
import sys
from datetime import datetime, timedelta

# Support both direct execution and package import
try:
    from .utils.sandbox import Sandbox
    from .agents.configuration import Configuration
    from .config import Config
    from .utils.waiting_list import WaitingList
    from .utils.conflict_list import ConflictList
    from .utils.integrate_dockerfile import integrate_dockerfile
except ImportError:
    from utils.sandbox import Sandbox
    from agents.configuration import Configuration
    from config import Config
    from utils.waiting_list import WaitingList
    from utils.conflict_list import ConflictList
    from utils.integrate_dockerfile import integrate_dockerfile

import subprocess
import ast
import shutil

# Save original stderr at module level BEFORE any redirection
original_stderr = sys.stderr

class TeeOutput:
    """Writes output to both stdout and a log file simultaneously"""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', buffering=1)  # Line buffering
        
    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()  # Immediate flush for real-time output
        self.log.write(message)
        self.log.flush()
        
    def flush(self):
        self.terminal.flush()
        self.log.flush()
        
    def close(self):
        self.log.close()

def move_files_to_repo(source_folder):
    target_folder = os.path.join(source_folder, 'repo_inner_directory_long_long_name_to_avoid_duplicate')
    
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)
    
    for item in os.listdir(source_folder):
        item_path = os.path.join(source_folder, item)
        
        if item == 'repo_inner_directory_long_long_name_to_avoid_duplicate':
            continue
        
        shutil.move(item_path, os.path.join(target_folder, item))

    os.rename(target_folder, os.path.join(source_folder, 'repo'))

# Download repo to utils/repo folder, remove the outermost folder, and remove any existing Dockerfile
def download_repo(root_path, full_name, sha, output_root=None):
    if len(full_name.split('/')) != 2:
        raise Exception("full_name Wrong!!!")
    author_name = full_name.split('/')[0]
    repo_name = full_name.split('/')[1]
    repo_path = f'{root_path}/utils/repo/{author_name}/{repo_name}/repo'
    
    # Increase git buffer for large repos (500MB buffer, no speed limits)
    git_config_cmd = "git config --global http.postBuffer 524288000 && git config --global http.lowSpeedLimit 0 && git config --global http.lowSpeedTime 999999"
    subprocess.run(git_config_cmd, shell=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Repository Reuse Logic (v2.3)
    # ═══════════════════════════════════════════════════════════════
    
    if os.path.exists(f'{repo_path}/.git'):
        # Repository already exists! Try to reuse it
        print(f"🔄 Repository {full_name} already exists, checking current commit...")
        
        try:
            # Get current commit
            current_commit_result = subprocess.run(
                'git rev-parse HEAD',
                cwd=repo_path,
                capture_output=True,
                text=True,
                shell=True
            )
            current_commit = current_commit_result.stdout.strip()
            
            if current_commit.startswith(sha) or sha.startswith(current_commit[:8]):
                # Already at target commit!
                print(f"✅ Already at commit {sha[:8]}, skipping fetch and checkout")
                return  # Early exit - fastest path!
            
            # Different commit, need to switch
            print(f"📍 Current: {current_commit[:8]}, target: {sha[:8]}")
            print(f"🧹 Cleaning local changes...")
            
            # Clean any local modifications
            subprocess.run('git reset --hard HEAD', cwd=repo_path, shell=True, capture_output=True)
            subprocess.run('git clean -fdx', cwd=repo_path, shell=True, capture_output=True)
            
            # Try to checkout target commit (might already be fetched)
            checkout_result = subprocess.run(
                f'git checkout {sha}',
                cwd=repo_path,
                capture_output=True,
                shell=True
            )
            
            if checkout_result.returncode == 0:
                print(f"✅ Successfully switched to commit {sha[:8]} (already fetched)")
                return
            
            # Commit not found locally, need to fetch
            print(f"📥 Fetching latest changes...")
            fetch_result = subprocess.run(
                'git fetch origin',
                cwd=repo_path,
                capture_output=True,
                shell=True,
                timeout=300
            )
            
            if fetch_result.returncode != 0:
                print(f"⚠️  Fetch failed, trying specific commit...")
                subprocess.run(f'git fetch origin {sha}', cwd=repo_path, shell=True, timeout=300)
            
            # Now checkout
            subprocess.run(f'git checkout {sha}', cwd=repo_path, shell=True, check=True)
            print(f"✅ Successfully updated to commit {sha[:8]}")
            return
            
        except Exception as e:
            print(f"⚠️  Error reusing repository: {e}")
            print(f"🔄 Will try to clone fresh...")
            # Remove corrupted repo and continue to clone
            subprocess.run(f'rm -rf {repo_path}', shell=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Fresh Clone (first time or after error)
    # ═══════════════════════════════════════════════════════════════
    
    if not os.path.exists(f'{root_path}/utils/repo/{author_name}/{repo_name}'):
        os.system(f'mkdir -p {root_path}/utils/repo/{author_name}/{repo_name}')
    
    # Retry logic for unstable network connections
    download_cmd = f"git clone https://github.com/{full_name}.git"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"📦 Cloning {full_name} (attempt {attempt + 1}/{max_retries})...")
            subprocess.run(download_cmd, cwd=f'{root_path}/utils/repo/{author_name}', check=True, shell=True, timeout=600)
            print(f"✅ Successfully cloned {full_name}")
            break
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Clone attempt {attempt + 1} failed, retrying in 5 seconds...")
                time.sleep(5)
            else:
                print(f"❌ Failed to clone repository from GitHub after {max_retries} attempts: {full_name}")
                print(f"Error: {e}")
                raise Exception(f"Cannot clone repository {full_name}. Please check network connection and repository accessibility.")
    
    move_files_to_repo(f'{root_path}/utils/repo/{author_name}/{repo_name}')
    if os.path.exists(f"{repo_path}/Dockerfile") and not os.path.isdir(f"{repo_path}/Dockerfile"):
        rm_dockerfile_cmd = f"rm -rf {repo_path}/Dockerfile"
        subprocess.run(rm_dockerfile_cmd, check=True, shell=True)

    checkout_cmd = f"git checkout {sha}"
    subprocess.run(checkout_cmd, cwd=repo_path, capture_output=True, shell=True)
    
    # Create output directory structure if needed
    if output_root:
        author_name = full_name.split('/')[0]
        repo_name = full_name.split('/')[1]
        if not os.path.exists(f'{output_root}/output/{author_name}/{repo_name}'):
            os.makedirs(f'{output_root}/output/{author_name}/{repo_name}', exist_ok=True)
        with open(f'{output_root}/output/{author_name}/{repo_name}/sha.txt', 'w') as w1:
            w1.write(sha)

def run_build(repository, commit, root_path='.'):
    """Core build logic extracted from main()"""
    
    waiting_list = WaitingList()
    conflict_list = ConflictList()

    if not os.path.isabs(root_path):
        root_path = os.path.abspath(root_path)
    
    # root_path should point to build_agent directory
    if not root_path.endswith('build_agent'):
        root_path = os.path.join(root_path, 'build_agent')

    full_name = repository
    sha = commit
    
    # Determine output_root (must be root_path for compatibility with legacy code)
    # Config.OUTPUT_ROOT is relative to root_path, but output_root itself should be root_path
    # because code uses {output_root}/output/{repo}/...
    if os.path.isabs(Config.OUTPUT_ROOT):
        # If absolute path, use it directly (but this is unusual)
        output_root = Config.OUTPUT_ROOT
    else:
        # Use root_path as output_root (legacy compatible)
        # This ensures paths like {output_root}/output/{repo}/ work correctly
        output_root = root_path
    
    # Setup automatic logging in project-specific directory
    project_output_dir = os.path.join(output_root, 'output', full_name.split('/')[0], full_name.split('/')[1])
    os.makedirs(project_output_dir, exist_ok=True)
    log_file = os.path.join(project_output_dir, f"{full_name.replace('/', '_')}_{sha[:7]}.log")
    tee = TeeOutput(log_file)
    sys.stdout = tee
    sys.stderr = tee
    
    print(f"ABLE - Automated C/C++ Build Environment Configuration")
    print(f"Model: {Config.LLM_MODEL}")
    print(f"Repository: {full_name}")
    print(f"Commit: {sha}")
    print(f"Max turns: {Config.MAX_TURN}")
    print(f"Log file: {log_file}")
    print("-" * 70)
    
    # Check for old-style patch directory (legacy compatibility)
    old_patch_path = f'{output_root}/output/{full_name}/patch'
    if os.path.exists(old_patch_path):
        rm_cmd = f"rm -rf {old_patch_path}"
        subprocess.run(rm_cmd, shell=True, check=True)
    if not os.path.exists(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}'):
        subprocess.run(f'mkdir -p {output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}', shell=True)
    
    download_repo(root_path, full_name, sha, output_root)

    trajectory = []

    # Use C-specific image
    docker_image = Config.DOCKER_IMAGE
    configuration_sandbox = Sandbox(docker_image, full_name, root_path)
    configuration_sandbox.start_container()
    configuration_agent = Configuration(configuration_sandbox, docker_image, full_name, root_path)
    msg, outer_commands = configuration_agent.run('/tmp', trajectory, waiting_list, conflict_list)
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/track.json', 'w') as w1:
        w1.write(json.dumps(msg, indent=4))
    commands = configuration_sandbox.stop_container()
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/inner_commands.json', 'w') as w2:
        w2.write(json.dumps(commands, indent=4))
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/outer_commands.json', 'w') as w3:
        w3.write(json.dumps(outer_commands, indent=4))
    
    # Check if runtest passed
    runtest_passed = False
    test_txt_path = f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/test.txt'
    if os.path.exists(test_txt_path):
        with open(test_txt_path, 'r') as f:
            runtest_passed = "Congratulations" in f.read()
    
    # Generate Dockerfile
    dockerfile_output_path = f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}'
    try:
        integrate_dockerfile(dockerfile_output_path)
        with open(f'{dockerfile_output_path}/track.txt', 'a') as a1:
            a1.write('Dockerfile generation: ✅ SUCCESS\n')
    except Exception as e:
        with open(f'{dockerfile_output_path}/track.txt', 'a') as a1:
            a1.write(f'Dockerfile generation: ❌ FAILED\n{e}\n')
    
    # 🆕 P3.3: Verify Dockerfile can be built (only if runtest passed)
    def verify_dockerfile(output_path, full_name, root_path):
        """
        Verify that the generated Dockerfile can actually be built.
        Returns True if build succeeds, False otherwise.
        """
        dockerfile_path = f"{output_path}/Dockerfile"
        if not os.path.exists(dockerfile_path):
            return False, "Dockerfile not found"
        
        # Create a unique test image name (must be lowercase for Docker)
        test_image = f"able_test_{full_name.replace('/', '_').lower()}_{int(time.time())}"
        
        # Use the actual build_agent directory passed via root_path
        build_context = os.path.abspath(root_path)
        if not os.path.isdir(build_context):
            return False, f"Build context not found: {build_context}"
        dockerfile_rel_path = os.path.relpath(dockerfile_path, build_context)
        build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", test_image, build_context]
        
        try:
            print(f"\n{'='*70}")
            print(f"🔍 Verifying Dockerfile build...")
            print(f"{'='*70}")
            
            result = subprocess.run(
                build_cmd,
                timeout=600,  # 10 minutes timeout
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print()
                print("╔══════════════════════════════════════════════════════════════════════════╗")
                print("║                   ✅ DOCKERFILE BUILD: SUCCESS                            ║")
                print("╚══════════════════════════════════════════════════════════════════════════╝")
                print(f"📦 Project: {full_name}")
                print(f"✅ Docker build completed successfully")
                print()
                
                # Clean up test image
                cleanup_cmd = ["docker", "rmi", test_image]
                subprocess.run(cleanup_cmd, capture_output=True)
                
                return True, "Build successful"
            else:
                print()
                print("╔══════════════════════════════════════════════════════════════════════════╗")
                print("║                   ❌ DOCKERFILE BUILD: FAILED                             ║")
                print("╚══════════════════════════════════════════════════════════════════════════╝")
                print(f"📦 Project: {full_name}")
                print(f"❌ Docker build failed")
                print()
                print(f"Error output (last 50 lines):")
                error_lines = result.stderr.split('\n')[-50:]
                print('\n'.join(error_lines))
                print()
                
                return False, f"Build failed: {result.stderr[-500:]}"
                
        except subprocess.TimeoutExpired:
            msg = "Dockerfile build timed out (>10 minutes)"
            print(f"⏱️  {msg}")
            return False, msg
            
        except Exception as e:
            msg = f"Dockerfile verification error: {str(e)}"
            print(f"❌ {msg}")
            return False, msg
    
    # Verify Dockerfile (only if runtest passed)
    if runtest_passed:
        dockerfile_valid, verification_msg = verify_dockerfile(
            dockerfile_output_path,
            full_name,
            root_path
        )
        with open(f'{dockerfile_output_path}/dockerfile_verification.txt', 'w') as f:
            f.write(f"Valid: {dockerfile_valid}\n")
            f.write(f"Message: {verification_msg}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
    else:
        print()
        print("⏭️  Skipping Dockerfile verification (runtest did not pass)")
        print()
        with open(f'{dockerfile_output_path}/dockerfile_verification.txt', 'w') as f:
            f.write(f"Valid: False\n")
            f.write(f"Message: Skipped - runtest did not pass\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Close log file and restore stdout
    if hasattr(sys.stdout, 'close') and hasattr(sys.stdout, 'terminal'):
        terminal = sys.stdout.terminal  # Save reference before closing
        sys.stdout.close()
        sys.stdout = terminal

    return runtest_passed

def main():
    """Legacy entry point for backwards compatibility"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ABLE - Automated C/C++ Build Environment Configuration')
    parser.add_argument('full_name', type=str, help='Repository full name (e.g., ImageMagick/ImageMagick)')
    parser.add_argument('sha', type=str, help='Git commit SHA')
    parser.add_argument('root_path', type=str, help='Root path (build_agent directory)')
    parser.add_argument('--model', type=str, help=f'LLM model to use (default: {Config.LLM_MODEL})')
    parser.add_argument('--max-turns', type=int, help=f'Maximum turns (default: {Config.MAX_TURN})')
    parser.add_argument('--output', type=str, help=f'Output directory (default: {Config.OUTPUT_ROOT})')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Apply CLI overrides
    if args.model:
        Config.LLM_MODEL = args.model
    if args.max_turns:
        Config.MAX_TURN = args.max_turns
    if args.output:
        Config.OUTPUT_ROOT = args.output
    if args.verbose:
        Config.VERBOSE = True
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(2)
    
    return run_build(args.full_name, args.sha, args.root_path)


if __name__ == '__main__':
    try:
        subprocess.run('docker rmi $(docker images --filter "dangling=true" -q) > /dev/null 2>&1', shell=True)
    except:
        print("No dangling images")
    
    start_time = time.time()
    result = False
    try:
        result = main()
    finally:
        # v3.0 FIX: Restore stderr FIRST (critical for exit code 120!)
        sys.stderr = original_stderr
        # Ensure log file is closed even on errors
        if hasattr(sys.stdout, 'close') and hasattr(sys.stdout, 'terminal'):
            terminal = sys.stdout.terminal  # Save reference before closing
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f'Total execution time: {elapsed_time:.2f} seconds')
            sys.stdout.close()
            sys.stdout = terminal
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f'Total execution time: {elapsed_time:.2f} seconds')
    if not result:
        sys.exit(1)
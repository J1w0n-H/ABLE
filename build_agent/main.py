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
import threading
import time
import os
import sys
import subprocess
import shutil
from agents.configuration import Configuration
from utils.sandbox import Sandbox

def move_files_to_repo(source_folder):
    """Move files to repo directory structure"""
    target_folder = os.path.join(source_folder, 'repo_inner_directory_long_long_name_to_avoid_duplicate')
    
    # Check if target folder exists, create if it doesn't
    if not os.path.exists(target_folder):
        os.mkdir(target_folder)
    
    # Iterate through all files and folders in source folder
    for item in os.listdir(source_folder):
        item_path = os.path.join(source_folder, item)
        
        # Skip the target folder
        if item == 'repo_inner_directory_long_long_name_to_avoid_duplicate':
            continue
        
        # Move files or folders to target folder
        shutil.move(item_path, os.path.join(target_folder, item))

    os.rename(target_folder, os.path.join(source_folder, 'repo'))

def download_repo(root_path, full_name, sha):
    """Download C repository and prepare for building"""
    if len(full_name.split('/')) != 2:
        raise Exception("full_name Wrong!!!")
    
    author_name = full_name.split('/')[0]
    repo_name = full_name.split('/')[1]
    
    if not os.path.exists(f'{root_path}/utils/repo/{author_name}/{repo_name}'):
        os.system(f'mkdir -p {root_path}/utils/repo/{author_name}/{repo_name}')
    
    # Clone repository
    download_cmd = f"git clone https://github.com/{full_name}.git"
    try:
        subprocess.run(download_cmd, cwd=f'{root_path}/utils/repo/{author_name}', check=True, shell=True)
    except subprocess.CalledProcessError:
        print(f"Failed to clone from GitHub, using local repository if available")
        if os.path.exists(f'{root_path}/utils/repo/{author_name}/{repo_name}'):
            print(f"Using existing local repository: {full_name}")
        else:
            raise
    
    # Reorganize files
    move_files_to_repo(f'{root_path}/utils/repo/{author_name}/{repo_name}')
    
    # Remove existing Dockerfile if present
    if os.path.exists(f"{root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile") and not os.path.isdir(f"{root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile"):
        rm_dockerfile_cmd = f"rm -rf {root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile"
        subprocess.run(rm_dockerfile_cmd, check=True, shell=True)
    
    # Checkout specific commit
    checkout_cmd = f"git checkout {sha}"
    subprocess.run(checkout_cmd, cwd=f'{root_path}/utils/repo/{author_name}/{repo_name}/repo', capture_output=True, shell=True)

    # Save SHA
    output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
    if not os.path.exists(f'{output_root}/output/{author_name}/{repo_name}'):
        os.makedirs(f'{output_root}/output/{author_name}/{repo_name}', exist_ok=True)
    with open(f'{output_root}/output/{author_name}/{repo_name}/sha.txt', 'w') as w1:
        w1.write(sha)

def main():
    parser = argparse.ArgumentParser(description='Build C project with Docker environment.')
    parser.add_argument('full_name', type=str, help='The full name of the repository (e.g., user/repo).')
    parser.add_argument('sha', type=str, help='Git commit SHA')
    parser.add_argument('root_path', type=str, help='Root path')
    
    args = parser.parse_args()

    root_path = args.root_path
    if not os.path.isabs(root_path):
        root_path = os.path.abspath(root_path)

    full_name = args.full_name
    sha = args.sha
    
    print(f"Processing C repository: {full_name}")
    print(f"Commit SHA: {sha}")
    
    # Setup output directories
    output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
    if os.path.exists(f'{output_root}/output/{full_name}/patch'):
        rm_cmd = f"rm -rf {output_root}/output/{full_name}/patch"
        subprocess.run(rm_cmd, shell=True, check=True)
    
    if not os.path.exists(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}'):
        subprocess.run(f'mkdir -p {output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}', shell=True)
    
    # Clean up existing repo
    if os.path.exists(f'{root_path}/utils/repo/{full_name}'):
        init_cmd = f"rm -rf {root_path}/utils/repo/{full_name} && mkdir -p {root_path}/utils/repo/{full_name}"
    else:
        init_cmd = f"mkdir -p {root_path}/utils/repo/{full_name}"
    subprocess.run(init_cmd, check=True, shell=True)
    
    # Setup timeout timer
    def timer():
        time.sleep(3600*2)  # Wait for 2 hours
        print("Timeout for 2 hour!")
        os._exit(1)  # Force exit the program

    # Start timer thread
    timer_thread = threading.Thread(target=timer)
    timer_thread.daemon = True
    timer_thread.start()

    # Download repository
    download_repo(root_path, full_name, sha)

    trajectory = []

    # Create C-specific sandbox
    configuration_sandbox = Sandbox("gcr.io/oss-fuzz-base/base-builder", full_name, root_path)
    configuration_sandbox.start_container()
    configuration_agent = Configuration(configuration_sandbox, 'gcr.io/oss-fuzz-base/base-builder', full_name, root_path, 100)
    
    # Run configuration agent
    msg, outer_commands = configuration_agent.run('/tmp', trajectory)
    
    # Save results
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/track.json', 'w') as w1:
        w1.write(json.dumps(msg, indent=4))
    
    commands = configuration_sandbox.stop_container()
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/inner_commands.json', 'w') as w2:
        w2.write(json.dumps(commands, indent=4))
    
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/outer_commands.json', 'w') as w3:
        w3.write(json.dumps(outer_commands, indent=4))
    
    # Generate Dockerfile
    try:
        from utils.integrate_dockerfile import integrate_dockerfile
        integrate_dockerfile(f'{output_root}/output/{full_name}')
        msg = f'Generate success!'
        with open(f'{output_root}/output/{full_name}/track.txt', 'a') as a1:
            a1.write(msg + '\n')
    except Exception as e:
        msg = f'integrate_docker failed, reason:\n {e}'
        with open(f'{output_root}/output/{full_name}/track.txt', 'a') as a1:
            a1.write(msg + '\n')

if __name__ == '__main__':
    try:
        subprocess.run('docker rmi $(docker images --filter "dangling=true" -q) > /dev/null 2>&1', shell=True)
    except:
        print("No dangling images")
    
    start_time = time.time()
    main()
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f'Total execution time: {elapsed_time:.2f} seconds')

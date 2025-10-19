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
from utils.sandbox import Sandbox
from agents.configuration import Configuration
import subprocess
from utils.waiting_list import WaitingList
from utils.conflict_list import ConflictList
from utils.integrate_dockerfile import integrate_dockerfile
import ast
import shutil

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
    # Define the path where the target folder is located
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

# Download repo to utils/repo folder, remove the outermost folder, and remove any existing Dockerfile
def download_repo(root_path, full_name, sha):
    if len(full_name.split('/')) != 2:
        raise Exception("full_name Wrong!!!")
    author_name = full_name.split('/')[0]
    repo_name = full_name.split('/')[1]
    if not os.path.exists(f'{root_path}/utils/repo/{author_name}/{repo_name}'):
        os.system(f'mkdir -p {root_path}/utils/repo/{author_name}/{repo_name}')
    download_cmd = f"git clone https://github.com/{full_name}.git"
    try:
        subprocess.run(download_cmd, cwd=f'{root_path}/utils/repo/{author_name}', check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to clone repository from GitHub: {full_name}")
        print(f"Error: {e}")
        raise Exception(f"Cannot clone repository {full_name}. Please check network connection and repository accessibility.")
    
    move_files_to_repo(f'{root_path}/utils/repo/{author_name}/{repo_name}')
    if os.path.exists(f"{root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile") and not os.path.isdir(f"{root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile"):
        rm_dockerfile_cmd = f"rm -rf {root_path}/utils/repo/{author_name}/{repo_name}/repo/Dockerfile"
        subprocess.run(rm_dockerfile_cmd, check=True, shell=True)


    checkout_cmd = f"git checkout {sha}"
    subprocess.run(checkout_cmd, cwd=f'{root_path}/utils/repo/{author_name}/{repo_name}/repo', capture_output=True, shell=True)

    # x = subprocess.run('git log -1 --format="%H"', cwd=f'{root_path}/utils/repo/{author_name}/{repo_name}/repo', capture_output=True, shell=True)
    output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
    if not os.path.exists(f'{output_root}/output/{author_name}/{repo_name}'):
        os.makedirs(f'{output_root}/output/{author_name}/{repo_name}', exist_ok=True)
    with open(f'{output_root}/output/{author_name}/{repo_name}/sha.txt', 'w') as w1:
        w1.write(sha)

def main():
    # subprocess.run('docker rm -f $(docker ps -aq)', shell=True)
    parser = argparse.ArgumentParser(description='Run script with repository full name as an argument.')
    parser.add_argument('full_name', type=str, help='The full name of the repository (e.g., user/repo).')
    parser.add_argument('sha', type=str, help='sha')
    parser.add_argument('root_path', type=str, help='root path')
    
    args = parser.parse_args()

    waiting_list = WaitingList()
    conflict_list = ConflictList()

    root_path = args.root_path

    if not os.path.isabs(root_path):
        root_path = os.path.abspath(root_path)
    
    # root_path should point to build_agent directory
    if not root_path.endswith('build_agent'):
        root_path = os.path.join(root_path, 'build_agent')

    full_name = args.full_name
    sha = args.sha
    
    output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
    
    # 🆕 Setup automatic logging
    log_dir = os.path.join(output_root, 'log')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{full_name.replace('/', '_')}_{sha[:7]}.log")
    tee = TeeOutput(log_file)
    sys.stdout = tee
    sys.stderr = tee
    
    print(f"ARVO2.0 - Automated C/C++ Build Environment Configuration")
    print(f"Log file: {log_file}")
    print(f"Repository: {full_name}")
    print(f"Commit: {sha}")
    print("-" * 70)
    
    # if os.path.exists(f'{root_path}/{full_name}/TIMEOUT'):
    #     sys.exit(123)
    
    if os.path.exists(f'{output_root}/output/{full_name}/patch'):
        rm_cmd = f"rm -rf {output_root}/output/{full_name}/patch"
        subprocess.run(rm_cmd, shell=True, check=True)
    if not os.path.exists(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}'):
        subprocess.run(f'mkdir -p {output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}', shell=True)
    if os.path.exists(f'{root_path}/utils/repo/{full_name}'):
        init_cmd = f"rm -rf {root_path}/utils/repo/{full_name} && mkdir -p {root_path}/utils/repo/{full_name}"
    else:
        init_cmd = f"mkdir -p {root_path}/utils/repo/{full_name}"
    subprocess.run(init_cmd, check=True, shell=True)
    
    def timer():
        time.sleep(3600*2)  # Wait for 2 hours
        print("Timeout for 2 hour!")
        os._exit(1)  # Force exit the program

    # Start timer thread
    timer_thread = threading.Thread(target=timer)
    timer_thread.daemon = True
    timer_thread.start()

    download_repo(root_path, full_name, sha)

    trajectory = []

    # C 전용 이미지 사용
    configuration_sandbox = Sandbox("gcr.io/oss-fuzz-base/base-builder", full_name, root_path)
    configuration_sandbox.start_container()
    configuration_agent = Configuration(configuration_sandbox, 'gcr.io/oss-fuzz-base/base-builder', full_name, root_path, 100)
    msg, outer_commands = configuration_agent.run('/tmp', trajectory, waiting_list, conflict_list)
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/track.json', 'w') as w1:
        w1.write(json.dumps(msg, indent=4))
    commands = configuration_sandbox.stop_container()
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/inner_commands.json', 'w') as w2:
        w2.write(json.dumps(commands, indent=4))
    with open(f'{output_root}/output/{full_name.split("/")[0]}/{full_name.split("/")[1]}/outer_commands.json', 'w') as w3:
        w3.write(json.dumps(outer_commands, indent=4))
    try:
        integrate_dockerfile(f'{output_root}/output/{full_name}')
        msg = f'Generate success!'
        with open(f'{output_root}/output/{full_name}/track.txt', 'a') as a1:
            a1.write(msg + '\n')
    except Exception as e:
        msg = f'integrate_docker failed, reason:\n {e}'
        with open(f'{output_root}/output/{full_name}/track.txt', 'a') as a1:
            a1.write(msg + '\n')
    
    # 🆕 Close log file
    if hasattr(sys.stdout, 'close') and hasattr(sys.stdout, 'terminal'):
        sys.stdout.close()
        sys.stdout = sys.stdout.terminal

if __name__ == '__main__':
    try:
        subprocess.run('docker rmi $(docker images --filter "dangling=true" -q) > /dev/null 2>&1', shell=True)
    except:
        print("No dangling images")
    
    start_time = time.time()
    try:
        main()
    finally:
        # Ensure log file is closed even on errors
        if hasattr(sys.stdout, 'close') and hasattr(sys.stdout, 'terminal'):
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f'Spend totally {elapsed_time}.')
            sys.stdout.close()
            sys.stdout = sys.stdout.terminal
        else:
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f'Spend totally {elapsed_time}.')
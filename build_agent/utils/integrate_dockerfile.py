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


import json
import os
import re

def extract_package_name(command):
    """Extract package name from apt_install command"""
    parts = command.split()
    for i, part in enumerate(parts):
        if part == 'apt_install' and i + 1 < len(parts):
            return parts[i + 1]
    return ""

def generate_c_statement(inner_command):
    """Generate Dockerfile RUN statement for C commands"""
    command = inner_command['command']
    
    if 'run_make' in command:
        return 'RUN make'
    elif 'run_cmake' in command:
        return 'RUN cmake . && make'
    elif 'run_gcc' in command:
        return 'RUN gcc -o hello *.c'
    elif 'apt_install' in command:
        package = extract_package_name(command)
        return f'RUN apt-get update && apt-get install -y {package}'
    else:
        # Handle other shell commands
        return f'RUN {command}'

def integrate_dockerfile(root_path):
    """Generate final Dockerfile for C project"""
    dockerfile = []
    
    # Base image
    dockerfile.append('FROM gcr.io/oss-fuzz-base/base-builder')
    dockerfile.append('WORKDIR /')
    
    # Get repository info
    author_name = root_path.split('/')[-2]
    repo_name = root_path.split('/')[-1]
    
    # Clone repository
    dockerfile.append(f'RUN git clone https://github.com/{author_name}/{repo_name}.git')
    dockerfile.append('RUN mkdir /repo')
    dockerfile.append(f'RUN cp -r /{repo_name}/. /repo && rm -rf /{repo_name}/')
    
    # Checkout specific commit
    sha_file = f'{root_path}/sha.txt'
    if os.path.exists(sha_file):
        with open(sha_file, 'r') as f:
            sha = f.read().strip()
        dockerfile.append(f'RUN cd /repo && git checkout {sha}')
    
    # Add build commands
    commands_file = f'{root_path}/inner_commands.json'
    if os.path.exists(commands_file):
        with open(commands_file, 'r') as f:
            commands_data = json.load(f)
        
        for command in commands_data:
            if command.get('returncode', 1) == 0:  # Only successful commands
                statement = generate_c_statement(command)
                if statement:
                    dockerfile.append(statement)
    
    # Write Dockerfile
    dockerfile_path = f'{root_path}/Dockerfile'
    with open(dockerfile_path, 'w') as f:
        f.write('\n'.join(dockerfile))
    
    print(f"Dockerfile generated at: {dockerfile_path}")
    return dockerfile_path

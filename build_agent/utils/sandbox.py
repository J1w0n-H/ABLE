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


import subprocess
import time
import json
import os
import shutil
import re
from utils.agent_util import extract_commands, extract_diffs, append_trajectory

class Session:
    def __init__(self, container_name):
        self.container_name = container_name
        self.command_history = []

    def execute(self, command):
        """Execute command in Docker container"""
        self.command_history.append(command)
        
        # Handle C-specific commands
        if 'run_make' in command:
            return self._execute_make()
        elif 'run_cmake' in command:
            return self._execute_cmake()
        elif 'run_gcc' in command:
            return self._execute_gcc()
        elif 'apt_install' in command:
            return self._execute_apt_install(command)
        else:
            # Execute as regular shell command
            return self._execute_shell(command)

    def _execute_make(self):
        """Execute make build"""
        try:
            cmd = "docker exec {} bash -c 'cd /repo && make'".format(self.container_name)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Make build timed out"
        except Exception as e:
            return False, "", str(e)

    def _execute_cmake(self):
        """Execute cmake build"""
        try:
            cmd = "docker exec {} bash -c 'cd /repo && cmake . && make'".format(self.container_name)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "CMake build timed out"
        except Exception as e:
            return False, "", str(e)

    def _execute_gcc(self):
        """Execute direct gcc compilation"""
        try:
            cmd = "docker exec {} bash -c 'cd /repo && gcc -o hello *.c'".format(self.container_name)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "GCC compilation timed out"
        except Exception as e:
            return False, "", str(e)

    def _execute_apt_install(self, command):
        """Execute apt install command"""
        try:
            # Extract package name from command
            package = command.split()[-1]
            cmd = "docker exec {} bash -c 'apt-get update && apt-get install -y {}'".format(self.container_name, package)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Package installation timed out"
        except Exception as e:
            return False, "", str(e)

    def _execute_shell(self, command):
        """Execute regular shell command"""
        try:
            cmd = "docker exec {} bash -c '{}'".format(self.container_name, command)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)

    def execute_simple(self, command):
        """Execute simple command and return success/failure"""
        success, stdout, stderr = self.execute(command)
        return success, stdout + stderr

class Sandbox:
    def __init__(self, namespace, full_name, root_path):
        self.namespace = namespace
        self.full_name = full_name
        self.root_path = root_path
        self.container_name = None
        self.session = None

    def generate_dockerfile(self):
        """Generate Dockerfile for C projects"""
        dockerfile_content = f"""FROM {self.namespace}

# C build tools are already included in base-builder
# gcc, make, cmake, clang, etc. are pre-installed

RUN mkdir -p /repo && git config --global --add safe.directory /repo
"""
        
        dockerfile_path = f'{self.root_path}/utils/repo/{self.full_name}/Dockerfile'
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        return f'{self.root_path}/utils/repo/{self.full_name}'

    def start_container(self):
        """Start Docker container for C build"""
        # Generate Dockerfile
        dockerfile_dir = self.generate_dockerfile()
        
        # Build image
        image_name = f"c-build-{self.full_name.replace('/', '-')}"
        build_cmd = f"docker build -t {image_name} {dockerfile_dir}"
        subprocess.run(build_cmd, shell=True, check=True)
        
        # Set container name
        self.container_name = f"c-build-{self.full_name.replace('/', '-')}-container"
        
        # Remove existing container if it exists
        check_cmd = f"docker ps -aq -f name=^{self.container_name}$"
        result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print(f"Removing existing container: {self.container_name}")
            subprocess.run(f"docker stop {self.container_name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(f"docker rm {self.container_name}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Start container
        start_cmd = f"docker run -d --name {self.container_name} {image_name} tail -f /dev/null"
        subprocess.run(start_cmd, shell=True, check=True)
        
        # Copy repository files to container
        author_name = self.full_name.split('/')[0]
        repo_name = self.full_name.split('/')[1]
        repo_path = f"{self.root_path}/utils/repo/{author_name}/{repo_name}/repo"
        
        if os.path.exists(repo_path):
            copy_cmd = f"docker cp {repo_path}/. {self.container_name}:/repo/"
            subprocess.run(copy_cmd, shell=True, check=True)
        
        # Create session
        self.session = Session(self.container_name)
        return self.session

    def stop_container(self):
        """Stop container and return command history"""
        if self.container_name:
            # Get container logs and history
            logs_cmd = f"docker logs {self.container_name}"
            try:
                logs = subprocess.run(logs_cmd, shell=True, capture_output=True, text=True)
                logs_output = logs.stdout
            except:
                logs_output = ""
            
            # Stop and remove container
            stop_cmd = f"docker stop {self.container_name}"
            rm_cmd = f"docker rm {self.container_name}"
            subprocess.run(stop_cmd, shell=True)
            subprocess.run(rm_cmd, shell=True)
            
            # Return command history as JSON
            commands = []
            for i, cmd in enumerate(self.session.command_history):
                commands.append({
                    "command": cmd,
                    "returncode": 0,  # Assume success for now
                    "stdout": "",
                    "stderr": ""
                })
            
            return commands
        
        return []

    def get_session(self):
        """Get current session"""
        return self.session

# Test function
if __name__ == "__main__":
    sandbox = Sandbox("gcr.io/oss-fuzz-base/base-builder", "test/repo", "/tmp")
    sandbox.start_container()
    session = sandbox.get_session()
    
    # Test make command
    success, stdout, stderr = session.execute("run_make")
    print(f"Make result: {success}")
    print(f"Output: {stdout}")
    
    sandbox.stop_container()

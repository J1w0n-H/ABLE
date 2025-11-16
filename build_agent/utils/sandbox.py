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


import docker
import pexpect
import time 
import subprocess
import os 
import re
import glob
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parser.parse_command import match_download, match_runtest, match_conflict_solve, match_waitinglist_add, match_waitinglist_addfile, match_conflictlist_clear, match_waitinglist_clear, match_waitinglist_show, match_conflictlist_show, match_clear_configuration
from download import download
from outputcollector import OutputCollector
from helpers import truncate_msg, SAFE_COMMANDS
from error_parser import extract_critical_errors

# Feature flag for Command Pattern refactoring
USE_COMMAND_PATTERN = os.getenv('ARVO_USE_COMMAND_PATTERN', 'false').lower() == 'true'

# Legacy: keep for reference (now imported from helpers)
safe_cmd = SAFE_COMMANDS

def delete_dangling_image():
    # Get all dangling image IDs
    dangling_images = subprocess.check_output('docker images --filter "dangling=true" -q', shell=True).decode('utf-8').strip()
    # Delete dangling images if any exist
    if dangling_images:
        subprocess.run(f'docker rmi {dangling_images} > /dev/null 2>&1', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def compare_versions(version1, version2):
    # Split version strings
    parts1 = version1.split('.')
    parts2 = version2.split('.')

    # Pad shorter version list with zeros to match lengths
    max_len = max(len(parts1), len(parts2))
    parts1.extend(['0'] * (max_len - len(parts1)))
    parts2.extend(['0'] * (max_len - len(parts2)))

    # Compare version parts one by one
    for part1, part2 in zip(parts1, parts2):
        part1 = int(part1)
        part2 = int(part2)

        # Compare the two parts
        if part1 > part2:
            return 1
        elif part1 < part2:
            return -1

    # If all parts are equal, versions are equal
    return 0

class Sandbox:
    def __init__(self, namespace, repo_full_name, root_path):
        self.namespace = namespace
        self.client = docker.from_env(timeout=600)
        self.container = None
        self.shell = None
        self.commands = list()
        self.full_name = repo_full_name
        self.root_path = root_path
    
    def generate_dockerfile(self):
        """Generate Dockerfile for the build environment."""
        if self.namespace.startswith('gcr.io/oss-fuzz-base'):
            dockerfile_content = f"""FROM {self.namespace}

# C build tools (gcc, make, cmake, clang) are pre-installed in base-builder

RUN mkdir -p /repo && git config --global --add safe.directory /repo
"""
        else:
            dockerfile_content = f"""FROM {self.namespace}
RUN mkdir -p /repo && git config --global --add safe.directory /repo
"""
        dockerfile_path = f'{self.root_path}/utils/repo/{self.full_name}/Dockerfile'
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)
        return f'{self.root_path}/utils/repo/{self.full_name}'
    
    def build_image(self):
        dockerfile_path = self.generate_dockerfile()
        self.namespace = 'build_env_' + self.namespace

        try:
            subprocess.run(["docker", "build", ".", "-t", self.namespace], cwd=dockerfile_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Image build failed: {e}")
            return False
    
    def clear_configuration(self):
        """Reset container to initial state for C projects"""
        try:
            self.commit_container()
        except:
            pass
        # For C projects, restart with the same base image
        try:
            self.start_container()
        except Exception as e:
            self.switch_to_pre_image()
            return f'Clear configuration wrong! We have already rollback to the previous state.\n{e}'
        return self

    def commit_container(self):
        try:
            delete_dangling_image()
            image = self.container.commit(repository=f"{self.full_name.lower().replace('/', '_').replace('-', '_')}", tag='tmp')
            return True
        except docker.errors.ContainerError:
            return None

    def switch_to_pre_image(self):
        try:
            tmp_image_name = f"{self.full_name.lower().replace('/', '_').replace('-', '_')}:tmp"
            
            # Stop and remove existing container
            if self.container:
                self.container.stop()
                self.container.remove()
                delete_dangling_image()
            
            host_path = '/tmp/patch'
            container_path = '/tmp/patch'
            self.container = self.client.containers.run(
                tmp_image_name,
                detach=True,
                tty=True,
                stdin_open=True,
                volumes={host_path: {'bind': container_path, 'mode': 'rw'}},
                privileged=True,
                mem_limit='30g',
                network_mode='bridge',
                cpuset_cpus='0-15',
                )

            self.start_shell()
            return True
        
        except docker.errors.ImageNotFound:
            return False
        except docker.errors.ContainerError:
            return False
        except Exception:
            return False

    def get_project_path(self):
        project_path = self.container.exec_run("pwd").output.decode().strip()
        return project_path
    
    def start_container(self, base_image=False):
        if not base_image:
            success = self.build_image()
            if not success:
                raise Exception('Build image error!')
        image = f"{self.namespace}"
        host_path = '/tmp/patch'
        container_path = '/tmp/patch'
        try:
            if 'oss-fuzz' in image:
                self.container = self.client.containers.run(
                    image, 
                    command='/bin/bash',
                    detach=True, 
                    tty=True, 
                    stdin_open=True, 
                    privileged=True,
                    volumes={host_path: {'bind': container_path, 'mode': 'rw'}}
                    )
            else:
                self.container = self.client.containers.run(
                    image, 
                    detach=True, 
                    tty=True, 
                    stdin_open=True, 
                    privileged=True,
                    volumes={host_path: {'bind': container_path, 'mode': 'rw'}}
                    )

            source_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            cmd = f"chmod -R 777 {source_directory}/tools && docker cp {source_directory}/tools {self.container.name}:/home"
            subprocess.run(cmd, check=True, shell=True)

            cmd = f"docker cp {self.root_path}/utils/repo/{self.full_name}/repo {self.container.name}:/"
            subprocess.run(cmd, check=True, shell=True)
            return 1
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            if self.container is not None:
                try:
                    self.container.stop()
                    self.container.remove()
                except Exception:
                    pass
                finally:
                    self.container = None
            raise RuntimeError(f"Failed to start container while executing '{e.cmd}': {error_msg}") from e
        except Exception as e:
            if self.container is not None:
                try:
                    self.container.stop()
                    self.container.remove()
                except Exception:
                    pass
                finally:
                    self.container = None
            raise RuntimeError(f"Failed to start container: {e}") from e

    def start_shell(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True)
            command = f'docker exec -it -w /repo {self.container.id} /bin/bash'
            self.shell = pexpect.spawn(command, maxread=1000000)
            self.shell.expect([r'\$ ', r'# '], timeout=600)
        else:
            raise Exception("Container not started. Call start_container() first.")

    def get_session(self):
        self.start_shell()

        class Session:
            def __init__(self, sandbox):
                self.sandbox = sandbox
                
                # Initialize CommandExecutor if feature flag is enabled
                self.command_executor = None
                if USE_COMMAND_PATTERN:
                    try:
                        from command_handlers import CommandExecutor
                        self.command_executor = CommandExecutor()
                    except ImportError:
                        self.command_executor = None
            
            def get_returncode(self):
                echo_returncode = '''echo $?'''
                self.sandbox.shell.sendline(echo_returncode)
                self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
                output = self.sandbox.shell.before.decode('utf-8').strip()
                output = output.replace('\x1b[?2004l\r', '')

                output_lines1 = output.split('\r\n')

                if len(output_lines1) > 1:
                    last_line = output_lines1[-1]
                    output_lines1 = output_lines1[1:-1]
                    ansi_idx = last_line.find('''\x1b[''')
                    if ansi_idx != -1 and len(last_line[:ansi_idx].strip()) > 0:
                        output_lines1.append(last_line[:ansi_idx].strip())
                return_code = '\n'.join(output_lines1).strip()
                return int(return_code)

            def execute_simple(self, command, timeout=600):
                self.sandbox.commit_container()
                if command[-1] != '&':
                    start_time = time.time()
                    self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": '/'})
                    self.sandbox.shell.sendline(command + " ; sleep 0.5")
                    self.sandbox.commands[-1]["returncode"] = -1
                else:
                    start_time = time.time()
                    self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": '/'})
                    self.sandbox.shell.sendline(command)
                    self.sandbox.commands[-1]["returncode"] = -1

                self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
                end_time = time.time()
                elapsed_time = end_time - start_time
                self.sandbox.commands[-1]["time"] = elapsed_time

                output = self.sandbox.shell.before.decode('utf-8').strip()
                output = output.replace('\x1b[?2004l\r', '')
                output_lines = output.split('\r\n')

                if len(output_lines) > 1:
                    last_line = output_lines[-1]
                    output_lines = output_lines[1:-1]
                    ansi_idx = last_line.find('''\x1b[''')
                    if ansi_idx != -1 and len(last_line[:ansi_idx].strip()) > 0:
                        output_lines.append(last_line[:ansi_idx].strip())
                res = '\n'.join(output_lines).strip()
                if len(res.split(' ')) > 5000:
                    res_words = res.split(' ')
                    res = "The output is too long, so we've truncated it to show you the first and last 2500 words.\n"
                    res += (' '.join(res_words[:2500]) + '\n...\n' + ' '.join(res_words[-2500:]))
                return_code = self.get_returncode()
                self.sandbox.commands[-1]['returncode'] = return_code
                if str(return_code) == '0':
                    return True, res
                else:
                    self.sandbox.switch_to_pre_image()
                    return False, res

            def execute(self, command, waiting_list, conflict_list, timeout=600):
                """Execute command in container shell."""
                try:
                    if USE_COMMAND_PATTERN and self.command_executor:
                        return self.command_executor.execute(
                            command, self, waiting_list, conflict_list, timeout
                        )
                    
                    if 'hatch shell' == command.lower().strip():
                        return 'You are not allowed to use commands like `hatch shell` that would open a new shell!!!', -1
                    
                    if '$pwd$' == command.lower().strip():
                        command = 'pwd'
                        self.sandbox.shell.sendline(command)
                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            ansi_idx = last_line.find('''\x1b[''')
                            if ansi_idx != -1 and len(last_line[:ansi_idx].strip()) > 0:
                                output_lines.append(last_line[:ansi_idx].strip())
                        return output_lines[0], 0
                    
                    if '$pip list --format json$' == command.lower().strip():
                        command = 'pip list --format json'
                        self.sandbox.shell.sendline(command)
                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
                        
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')
                        
                        
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            ansi_idx = last_line.find('''\x1b[''')
                            if ansi_idx != -1 and len(last_line[:ansi_idx].strip()) > 0:
                                output_lines.append(last_line[:ansi_idx].strip())
                        return output_lines[0], 0

                    if match_download(command):
                        with OutputCollector() as collector:
                            download(self, waiting_list, conflict_list)
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, 'download'), 'unknown'
                    elif match_conflict_solve(command) != -1:
                        version_constraint = match_conflict_solve(command)['version_constraint']
                        unchanged = match_conflict_solve(command)['unchanged']
                        with OutputCollector() as collector:
                            conflict_list.solve(waiting_list, version_constraint, unchanged)
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_conflictlist_clear(command):
                        with OutputCollector() as collector:
                            conflict_list.clear()
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_waitinglist_add(command) != -1:
                        package_name = match_waitinglist_add(command)['package_name']
                        version_constraints = match_waitinglist_add(command)['version_constraints']
                        tool = match_waitinglist_add(command)['tool']
                        with OutputCollector() as collector:
                            waiting_list.add(package_name, version_constraints, tool, conflict_list)
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_waitinglist_addfile(command) != -1:
                        file_path = match_waitinglist_addfile(command)['file_path']
                        # Use self.sandbox.root_path instead of calculating from __file__
                        project_directory = self.sandbox.root_path
                        result = subprocess.run(f'docker cp {self.sandbox.container.name}:{file_path} {project_directory}/utils/repo/{self.sandbox.full_name}/repo', shell=True, capture_output=True)
                        if result.returncode != 0:
                            msg = f'\nRunning `{command}`...\n'
                            msg += f'The file {file_path} does not exist. Please ensure you have entered the correct absolute path, not a relative path! If you are unsure, you can use commands like `ls` to verify.'
                            return msg, 1
                        subprocess.run(f'sudo chown huruida:huruida {project_directory}/repo/{self.sandbox.full_name}/repo/{file_path.split("/")[-1]}', shell=True, capture_output=True)
                        with OutputCollector() as collector:
                            waiting_list.addfile(f'{project_directory}/utils/repo/{self.sandbox.full_name}/repo/{file_path.split("/")[-1]}', conflict_list)
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_waitinglist_clear(command):
                        with OutputCollector() as collector:
                            waiting_list.clear()
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_waitinglist_show(command):
                        with OutputCollector() as collector:
                            waiting_list.get_message()
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif match_conflictlist_show(command):
                        with OutputCollector() as collector:
                            conflict_list.get_message(waiting_list)
                        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
                        return truncate_msg(result_message, command), 'unknown'
                    elif 'pytest' in command.lower() and 'pip' not in command.lower():
                        msg = 'This is a C/C++ project. Use `runtest` instead (which runs ctest or make test for C/C++ projects).'
                        result_message = msg
                        return result_message, 1
                    elif command.split(' ')[0] == 'rm' and (command.split('/')[-1].startswith('test_') or command.split('/')[-1].endswith('_test.py')):
                        msg = 'Please do not directly delete the testing file to pass the test!'
                        result_message = msg
                        return result_message, 1
                    elif command.split(' ')[0] == 'mv' and (command.split('/')[-1].startswith('test_') or command.split('/')[-1].endswith('_test.py')):
                        msg = 'Please do not directly move the testing file to pass the test!'
                        result_message = msg
                        return result_message, 1
                    else:
                        if match_runtest(command):
                            command = 'python /home/tools/runtest.py'
                        if command == 'generate_diff':
                            command = 'python /home/tools/generate_diff.py'
                        
                        # v2.5: Dynamic timeout for apt-get commands
                        command_timeout = 600 * 2  # Default 20 minutes
                        if 'apt-get install' in command:
                            command_timeout = 1800  # 30 minutes for package installation
                        
                        if command[-1] != '&':
                            if not (command.split()[0].strip() in safe_cmd and '>' not in command):
                                self.sandbox.commit_container()
                            start_time = time.time()
                            dir, return_code = self.execute('$pwd$', waiting_list, conflict_list)
                            self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": dir})
                            # v3.9 FIX: Capture ACTUAL returncode (not sleep's!)
                            # Bug: " ; sleep 0.5" → $? returns 0 (sleep's exit code)
                            # Fix: ' ; echo "[[[RETURNCODE: $?]]]" ; sleep 0.5'
                            self.sandbox.shell.sendline(command + ' ; echo "[[[RETURNCODE: $?]]]" ; sleep 0.5')
                            self.sandbox.commands[-1]["returncode"] = -1
                        else:
                            if not (command.split()[0].strip() in safe_cmd and '>' not in command):
                                self.sandbox.commit_container()
                            start_time = time.time()
                            dir, return_code = self.execute('$pwd$', waiting_list, conflict_list)
                            self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": dir})
                            self.sandbox.shell.sendline(command)
                            self.sandbox.commands[-1]["returncode"] = -1

                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=command_timeout)
                        end_time = time.time()
                        elasped_time = end_time - start_time
                        self.sandbox.commands[-1]["time"] = elasped_time

                        
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')

                        # 🔧 v3.9: Parse returncode from marker FIRST (before output processing)
                        return_code = 0
                        if '[[[RETURNCODE:' in output:
                            try:
                                rc_start = output.rfind('[[[RETURNCODE:') + len('[[[RETURNCODE:')
                                rc_end = output.find(']]]', rc_start)
                                if rc_end != -1:
                                    rc_str = output[rc_start:rc_end].strip()
                                    if rc_str.isdigit() or (rc_str.startswith('-') and rc_str[1:].isdigit()):
                                        return_code = int(rc_str)
                                        # Remove marker from output
                                        output = output[:output.rfind('[[[RETURNCODE:')].rstrip()
                                    else:
                                        return_code = self.get_returncode()
                                else:
                                    return_code = self.get_returncode()
                            except Exception:
                                return_code = self.get_returncode()
                        else:
                            try:
                                return_code = self.get_returncode()
                            except pexpect.TIMEOUT:
                                return_code = 0
                            except pexpect.EOF:
                                return_code = 125
                            except Exception:
                                return_code = 0
                        
                        
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            ansi_idx = last_line.find('''\x1b[''')
                            if ansi_idx != -1 and len(last_line[:ansi_idx].strip()) > 0:
                                output_lines.append(last_line[:ansi_idx].strip())
                        
                        # Returncode already parsed above
                        try:
                            self.sandbox.commands[-1]["returncode"] = return_code
                        except:
                            self.sandbox.commands[-1]["returncode"] = 111
                            self.sandbox.commands[-1]["error_msg"] = return_code

                        if return_code != 0 and not (command == 'python /home/tools/runtest.py' and return_code == 5):
                            if command.strip().lower().startswith('conflict'):
                                msg = '''conflictlist command usage error, the following command formats are legal:
1. `conflictlist solve`
Explanation: The standalone `conflictlist solve` command means not to impose any version constraints, i.e., to default to downloading the latest version of the third-party library. This will update the version constraint in the waiting list to be unrestricted.
2. `conflictlist solve -v "==2.0"`
Explanation: Adding -v followed by a version constraint enclosed in double quotes updates the version constraint in the waiting list to that specific range, such as "==2.0", meaning to take version 2.0.
3. `conflictlist solve -v ">3.0"`
Explanation: Similar to the command 2, this constraint specifies a version number greater than 3.0.
4. `conflictlist solve -u`
Explanation: Adding -u indicates giving up all the constraints in the conflict list while still retaining the constraints in the waiting list, i.e., not updating the constraints for that library in the waiting list.
5. `conflictlist clear`
Explanation: Clear all the items in the conflict list.'''
                                result_message = f'Running `{command}`...\n' + msg + '\n'
    
                                return result_message, return_code
                            elif command.strip().lower().startswith('waiting'):
                                msg = '''waitinglist command usage error, the following command formats are leagal:
1. `waitinglist add -p package_name1 -t apt`
Explanation: Add package_name1 into waiting list(using apt-get), no version means install the latest available version by default.
2. `waitinglist addfile /path/to/file`
Explanation: Add all the items in the /path/to/file into waiting list. Note that you must make sure each line contains a valid package name.
3. `waitinglist clear`
Explanation: Clear all the items in the waiting list.'''
                                result_message = f'Running `{command}`...\n' + msg + '\n'
    
                                return result_message, return_code
                            # Keep environment on failure - retry until success
                            # DO NOT rollback immediately - let LLM try different approaches
                            output_lines.append('The command execution failed. Environment maintained for retry with a different approach.')
                        
                        result_message = '\n'.join(output_lines)
                        
                        # Extract and analyze errors (only on failure)
                        if return_code != 0:
                            # v2.5: Pass last_command for one-step fix generation
                            error_summary = extract_critical_errors(result_message, return_code, last_command=command)
                            if error_summary:
                                # Add error summary at the front
                                result_message = error_summary + "\n" + result_message
                            
                            # Suggest single-threaded build on parallel build failure
                            if 'make' in command and '-j' in command:
                                tip = "\n⚠️  Parallel build failed with complex output.\n"
                                tip += "💡 TIP: Try 'make' (single-thread) for clearer error messages.\n"
                                result_message = tip + result_message
                        if 'Congratulations, you have successfully configured the environment!' in result_message or command == 'python /home/tools/generate_diff.py'\
                            or command == 'pipdeptree --json-tree' or command == 'pipdeptree':
                            return result_message, return_code
                        else:
                            result_message = f'Running `{command}`...\n' + result_message + '\n'
                            return truncate_msg(result_message, command, returncode=return_code), return_code
                
                except pexpect.TIMEOUT:
                    if match_runtest(command):
                        os.sytem(f'touch {self.sandbox.root_path}/output/{self.sandbox.full_name}/TIMEOUT')
                        sys.exit(123)
                    partial_output = self.sandbox.shell.before.decode('utf-8').strip()
                    partial_output_lines = partial_output.split('\n')
                    if len(partial_output_lines) > 1:
                        partial_output_lines = partial_output_lines[1:-1]
                    partial_output = '\n'.join(partial_output_lines)
                    return f"Error: Command '{command}' timed out after {timeout} seconds. Partial output:\n + {partial_output}", 1

            def edit(self, edit_tmp_file:str, project_path:str, file_path = None, start_line = 0, end_line = 0, timeout=600):
                if file_path:
                    if file_path.split('/')[-1].startswith('test_') or file_path('/')[-1].endswith('_test.py'):
                        msg = f'Running Edit...\n' + f'You are trying to modify file {file_path}, but we require that you should not modify the testing files. Please consider alternative solutions.' + '\n'
                        return msg, 1
                if not file_path:
                    command = f"python /home/tools/code_edit.py -t '{edit_tmp_file}' -p '{project_path}'"
                else:
                    command = f"python /home/tools/code_edit.py -t '{edit_tmp_file}' -p '{project_path}' -f '{file_path}' -s {start_line} -e {end_line}"
                try:
                    start_time = time.time()
                    self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": '/'})
                    # Execute command in persistent shell
                    self.sandbox.shell.sendline(command)
                    end_time = time.time()
                    self.sandbox.commands[-1]["returncode"] = -1
                    elasped_time = end_time - start_time
                    self.sandbox.commands[-1]["time"] = elasped_time
                    self.sandbox.shell.expect([r'root@.*:.*# '], timeout=timeout)

                    
                    output = self.sandbox.shell.before.decode('utf-8').strip()
                
                    
                    output_lines = output.split('\r\n')
                    if len(output_lines) > 1:
                        output_lines = output_lines[1:-1]

                    result_message = f'Running Edit...\n' + '\n'.join(output_lines)
                    try:
                        return_code = self.get_returncode()
                    except pexpect.TIMEOUT:
                        return_code = 0
                    except pexpect.EOF:
                        return_code = 125
                    except Exception:
                        return_code = 0
                    self.sandbox.commands[-1]['returncode'] = return_code
                    return result_message, return_code

                except pexpect.TIMEOUT:
                    return 'Running Edit...\n' + f"Error: Edit timed out after {timeout} seconds." + '\n', 1
                
            def close(self):
                if self.sandbox.shell:
                    self.sandbox.shell.sendline('exit')
                    self.sandbox.shell.expect(pexpect.EOF)
                    self.sandbox.shell.close(force=True)
                    self.sandbox.shell = None

        return Session(self)

    def stop_container(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True)
                self.shell = None
            self.container.stop()
            self.container.remove()
            self.container = None
            subprocess.run(f"docker rmi {self.full_name.lower().replace('/', '_').replace('-', '_')}:tmp > /dev/null 2>&1", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return self.commands


if __name__ == "__main__":
    from conflict_list import ConflictList
    from waiting_list import WaitingList
    waiting_list = WaitingList()
    conflict_list = ConflictList()
    sandbox = Sandbox("python:3.10", "basf/MolPipeline")
    sandbox.start_container()
    session = sandbox.get_session()
    while True:
        a = input()
        result, return_code = session.execute(a, waiting_list, conflict_list)
        print('result:\n' + result)
        print('return_code:\n' + str(return_code))
    session.close()
    sandbox.stop_container()

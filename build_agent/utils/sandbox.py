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
import glob
import re
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parser.parse_command import match_download, match_runtest, match_conflict_solve, match_waitinglist_add, match_waitinglist_addfile, match_conflictlist_clear, match_waitinglist_clear, match_waitinglist_show, match_conflictlist_show, match_clear_configuration
from download import download
from outputcollector import OutputCollector
from show_msg import show_msg

# 这部分bash语句通常认为不会对于系统产生影响，如果下面safe_cmd打头，且不存在">"这样的重定向符，则不commit
safe_cmd = [
    "cd", "ls", "cat", "echo", "pwd", "whoami", "who", "date", "cal", "df", "du",
    "free", "uname", "uptime", "w", "ps", "pgrep", "top", "htop", "vmstat", "iostat",
    "dmesg", "tail", "head", "more", "less", "grep", "find", "locate", "whereis", "which",
    "file", "stat", "cmp", "diff", "md5sum", "sha256sum", "gzip", "gunzip", "bzip2", "bunzip2",
    "xz", "unxz", "sort", "uniq", "wc", "tr", "cut", "paste", "tee", "awk", "sed", "env", "printenv",
    "hostname", "ping", "traceroute", "ssh", "journalctl","lsblk", "blkid", "uptime",
    "lscpu", "lsusb", "lspci", "lsmod", "dmidecode", "ip", "ifconfig", "netstat", "ss", "route", "nmap",
    "strace", "ltrace", "time", "nice", "renice", "killall", "printf"
    ]

# 用来截断，传入result_message为字符串，command为运行指令，truncate为正常阈值，bar_truncate为保留疑似进度条数量
def truncate_msg(result_message, command, truncate=1000, bar_truncate=20, returncode=0):
    """
    Truncate command output intelligently:
    - Success (returncode=0): Show brief summary only
    - Failure (returncode!=0): Show full error details
    """
    lines = result_message.splitlines()
    lines = [x for x in lines if len(x.strip()) > 0]
    
    # 🆕 For successful commands, show brief summary only
    if returncode == 0:
        line_count = len(lines)
        
        # If output is reasonable, keep it
        if line_count <= 20 and len(result_message) <= 1000:
            return result_message
        
        # If output is long, show brief summary
        if line_count > 50 or len(result_message) > 5000:
            return f"Command executed successfully. Output: {line_count} lines, {len(result_message)} characters (truncated for brevity)."
        
        # Medium output: show first 10 and last 10 lines
        if line_count > 20:
            return '\n'.join(lines[:10] + ['...'] + lines[-10:])
    
    # For failed commands, show detailed output
    # 用来存疑似진행표시줄의 행수
    bar_lines = list()
    for i in range(len(lines)):
        line = lines[i]
        if line.strip().startswith('\x1b[') or line.count('\x1b[') >= 2 or line.count('█') >= 2 or '━━━━━' in line:
            bar_lines.append(i)
    if len(bar_lines) > bar_truncate:
        for i in range(len(lines)):
            if i in bar_lines[:-bar_truncate]:
                lines[i] = ''
    lines = [x for x in lines if len(x) > 0]

    result_message = '\n'.join(lines)
    res = result_message
    # 处리과長문장 - More aggressive truncation for C projects
    if len(result_message) > truncate * 3:
        res = f"Running `{command}`...\nThe output is too long, so we've truncated it to show you the first and last 3000 characters.\n"
        res += (result_message[:truncate*3] + "\n...[Truncation]...\n" + result_message[-truncate*3:])
    elif len(result_message.split(' ')) > truncate:
        res = f"Running `{command}`...\nThe output is too long, so we've truncated it to show you the first and last 1000 words.\n"
        res += (' '.join(result_message.split(' ')[:truncate]) + "\n...[Truncation]...\n" + ' '.join(result_message.split(' ')[-truncate:]))
    
    return res

def delete_dangling_image():
    # 获取所有 dangling 镜像的 ID
    dangling_images = subprocess.check_output('docker images --filter "dangling=true" -q', shell=True).decode('utf-8').strip()
    # 如果有 dangling 镜像，则删除它们
    if dangling_images:
        subprocess.run(f'docker rmi {dangling_images} > /dev/null 2>&1', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def compare_versions(version1, version2):
    # 分割版本号字符串
    parts1 = version1.split('.')
    parts2 = version2.split('.')

    # 将较短的版本号列表用零填充，使两者长度一致
    max_len = max(len(parts1), len(parts2))
    parts1.extend(['0'] * (max_len - len(parts1)))
    parts2.extend(['0'] * (max_len - len(parts2)))

    # 逐一比较版本号部分
    for part1, part2 in zip(parts1, parts2):
        part1 = int(part1)
        part2 = int(part2)

        # 比较两个部分
        if part1 > part2:
            return 1
        elif part1 < part2:
            return -1

    # 如果每个部分都相同，则版本号相等
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
        # C 전용 Dockerfile 생성
        if self.namespace.startswith('gcr.io/oss-fuzz-base'):
            # C 프로젝트용 Dockerfile
            dockerfile_content = f"""FROM {self.namespace}

# C build tools are already included in base-builder
# gcc, make, cmake, clang, etc. are pre-installed

RUN mkdir -p /repo && git config --global --add safe.directory /repo
"""
        else:
            # 기본 처리
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
            # subprocess.run(["docker", "build", ".", "--no-cache", "-t", self.namespace], cwd=dockerfile_path, check=True)
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
    
    # def change_base_image(self, base_image_name):
    #     try:
    #         self.commit_container()
    #     except:
    #         pass
    #     self.namespace = base_image_name.strip().lower()
    #     try:
    #         self.start_container()
    #     except Exception as e:
    #         self.switch_to_pre_image()
    #         return f'Change base image wrong! We have already rollback to the previous state. Please try another base image!\n{e}'
    #     return self


    def commit_container(self):
        try:
            delete_dangling_image()
            # 将容器提交成固定名称的镜像
            image = self.container.commit(repository=f"{self.full_name.lower().replace('/', '_').replace('-', '_')}", tag='tmp')
            # subprocess.run(f'docker commit {self.container.name} running_env:tmp', shell=True)
            # print(f"Container {self.container.name} committed as image running_env:tmp.")
            return True
        except docker.errors.ContainerError as e:
            print(f"Error committing container: {e}")
            return None

    def switch_to_pre_image(self):
        try:
            # tmp_image_name = "running_env:tmp"
            tmp_image_name = f"{self.full_name.lower().replace('/', '_').replace('-', '_')}:tmp"
            # print(f"Switching to tmp image: {tmp_image_name}")

            # 停止并移除现有的容器
            if self.container:
                self.container.stop()
                self.container.remove()
                delete_dangling_image()
            
            host_path = '/tmp/patch'
            container_path = '/tmp/patch'
            # 创建并启动一个新的容器，使用 tmp 镜像
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

            # 启动新的 shell 会话
            self.start_shell()
            return True
        
        except docker.errors.ImageNotFound as e:
            print(f"Image not found: {e}")
            return False
        except docker.errors.ContainerError as e:
            print(f"Error switching to tmp container: {e}")
            return False
        except Exception as generic_error:
            print(f"An unexpected error occurred: {generic_error}")
            return False

    # 获取容器内的项目路径
    def get_project_path(self):
        project_path = self.container.exec_run("pwd").output.decode().strip()
        return project_path
    
    # 开启一个新的Container，返回1表示创建成功，返回-1表示创建失败
    def start_container(self, base_image=False):
        if not base_image:
            success = self.build_image()
            if not success:
                # sys.exit(1)
                raise Exception('Build image error!')
        image = f"{self.namespace}"
        host_path = '/tmp/patch'
        container_path = '/tmp/patch'
        try:
            # For oss-fuzz images, override the default command to keep container running
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

            print(f"Container {self.container.name} {self.container.short_id} started with image {image}")
            
            current_file_path = os.path.abspath(__file__)
            current_directory = os.path.dirname(current_file_path)
            project_directory = os.path.dirname(current_directory)
            
            cmd = f"chmod -R 777 {project_directory}/tools && docker cp {project_directory}/tools {self.container.name}:/home"
            subprocess.run(cmd, check=True, shell=True)

            # 把utils/repo中的内容复制到根目录/中
            cmd = f"docker cp {project_directory}/utils/repo/{self.full_name}/repo {self.container.name}:/"
            subprocess.run(cmd, check=True, shell=True)
            return 1
        except Exception as e:
            print(f"Container start faild: {e}")
            return -1

    # 开启一个shell
    def start_shell(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True)  # 确保关闭之前的shell
            command = f'docker exec -it {self.container.id} /bin/bash'
            self.shell = pexpect.spawn(command)
            self.shell.expect([r'\$ ', r'# '], timeout=600)  # 等待bash提示符
        else:
            raise Exception("Container not started. Call start_container() first.")

    # 开启一个新的session
    def get_session(self):

        # 在获取session时启动新的shell
        self.start_shell()

        class Session:
            def __init__(self, sandbox):
                self.sandbox = sandbox
            
            def get_returncode(self):
                echo_returncode = '''echo $?'''
                self.sandbox.shell.sendline(echo_returncode)
                self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
                # 获取 shell.before 中匹配到的模式之前的输出
                output = self.sandbox.shell.before.decode('utf-8').strip()
                output = output.replace('\x1b[?2004l\r', '')

                # 分析输出行，排除发送的命令行和最后的提示符行
                output_lines1 = output.split('\r\n')

                if len(output_lines1) > 1:
                    last_line = output_lines1[-1]
                    output_lines1 = output_lines1[1:-1]
                    id = last_line.find('''\x1b[''')
                    if id != -1 and len(last_line[:id].strip()) > 0:
                        output_lines1.append(last_line[:id].strip())
                return_code = '\n'.join(output_lines1).strip()
                return int(return_code)


            # 给download用的一个特殊函数
            def execute_simple(self, command, timeout=600):
                self.sandbox.commit_container()
                if command[-1] != '&':
                    start_time = time.time()
                    self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": '/'})
                    self.sandbox.shell.sendline(command + " && sleep 0.5")
                    self.sandbox.commands[-1]["returncode"] = -1
                else:
                    start_time = time.time()
                    self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": '/'})
                    self.sandbox.shell.sendline(command)
                    self.sandbox.commands[-1]["returncode"] = -1

                self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)  # 等待bash提示符，带超时
                end_time = time.time()
                elasped_time = end_time - start_time
                self.sandbox.commands[-1]["time"] = elasped_time

                # 获取 shell.before 中匹配到的模式之前的输出
                output = self.sandbox.shell.before.decode('utf-8').strip()
                output = output.replace('\x1b[?2004l\r', '')

                # 分析输出行，排除发送的命令行和最后的提示符行
                output_lines = output.split('\r\n')

                if len(output_lines) > 1:
                    last_line = output_lines[-1]
                    output_lines = output_lines[1:-1]
                    id = last_line.find('''\x1b[''')
                    if id != -1 and len(last_line[:id].strip()) > 0:
                        output_lines.append(last_line[:id].strip())
                res = '\n'.join(output_lines).strip()
                if len(res.split(' ')) > 5000:
                    res = "The output is too long, so we've truncated it to show you the first and last 2500 words."
                    res += (' '.join(res.split(' ')[:2500]) + '\n' + ' '.join(res.splitlines()[-2500:]))
                return_code = self.get_returncode()
                self.sandbox.commands[-1]['returncode'] = return_code
                if str(return_code) == '0':
                    return True, res
                else:
                    self.sandbox.switch_to_pre_image()
                    return False, res

            def execute(self, command, waiting_list, conflict_list, timeout=600):
                try:
                    if 'hatch shell' == command.lower().strip():
                        return 'You are not allowed to use commands like `hatch shell` that would open a new shell!!!', -1
                    # 在持久shell中执行命令
                    if '$pwd$' == command.lower().strip():
                        command = 'pwd'
                        self.sandbox.shell.sendline(command)
                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)  # 等待bash提示符，带超时
                        # 获取 shell.before 中匹配到的模式之前的输出
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')
                        
                        # 分析输出行，排除发送的命令行和最后的提示符行
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            id = last_line.find('''\x1b[''')
                            if id != -1 and len(last_line[:id].strip()) > 0:
                                output_lines.append(last_line[:id].strip())
                        return output_lines[0], 0
                    
                    if '$pip list --format json$' == command.lower().strip():
                        command = 'pip list --format json'
                        self.sandbox.shell.sendline(command)
                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)  # 等待bash提示符，带超时
                        # 获取 shell.before 中匹配到的模式之前的输出
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')
                        
                        # 分析输出行，排除发送的命令行和最后的提示符行
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            id = last_line.find('''\x1b[''')
                            if id != -1 and len(last_line[:id].strip()) > 0:
                                output_lines.append(last_line[:id].strip())
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
                        current_file_path = os.path.abspath(__file__)
                        current_directory = os.path.dirname(current_file_path)
                        project_directory = os.path.dirname(current_directory)
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
                        msg = 'Please do not use `pytest` directly, but use `runtest` or `poetryruntest`(When you configured in poetry environment) instead. If there are something wrong when running `runtest` or `poetryruntest`, please solve it and run it again!'
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
                        if command[-1] != '&':
                            if not (command.split()[0].strip() in safe_cmd and '>' not in command):
                                self.sandbox.commit_container()
                            start_time = time.time()
                            dir, return_code = self.execute('$pwd$', waiting_list, conflict_list)
                            self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": dir})
                            self.sandbox.shell.sendline(command + " && sleep 0.5")
                            self.sandbox.commands[-1]["returncode"] = -1
                        else:
                            if not (command.split()[0].strip() in safe_cmd and '>' not in command):
                                self.sandbox.commit_container()
                            start_time = time.time()
                            dir, return_code = self.execute('$pwd$', waiting_list, conflict_list)
                            self.sandbox.commands.append({"command": command, "returncode": -2, "time": -1, "dir": dir})
                            self.sandbox.shell.sendline(command)
                            self.sandbox.commands[-1]["returncode"] = -1

                        self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600*2)  # 等待bash提示符，带超时
                        end_time = time.time()
                        elasped_time = end_time - start_time
                        self.sandbox.commands[-1]["time"] = elasped_time

                        # 获取 shell.before 中匹配到的模式之前的输出
                        output = self.sandbox.shell.before.decode('utf-8').strip()
                        output = output.replace('\x1b[?2004l\r', '')

                        # 分析输出行，排除发送的命令行和最后的提示符行
                        output_lines = output.split('\r\n')

                        if len(output_lines) > 1:
                            last_line = output_lines[-1]
                            output_lines = output_lines[1:-1]
                            id = last_line.find('''\x1b[''')
                            if id != -1 and len(last_line[:id].strip()) > 0:
                                output_lines.append(last_line[:id].strip())
                        try:
                            return_code = self.get_returncode()
                        except:
                            return_code = 123
                        try:
                            self.sandbox.commands[-1]["returncode"] = return_code
                        except:
                            self.sandbox.commands[-1]["returncode"] = 111
                            self.sandbox.commands[-1]["error_msg"] = return_code

                        if return_code != 0 and not ((command == 'python /home/tools/runtest.py' or command == 'python /home/tools/poetryruntest.py') and return_code == 5):
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
1. `waitinglist add -p package_name1 -v >=1.0.0 -t pip`
Explanation: Add package_name1>=1.0.0 into waiting list(using pip), and version constraints string cannot contain spaces.
2. `waitinglist add -p package_name1 -t pip`
Explanation: Add package_name1 into waiting list, no `-v` means download the latest version by default.
3. `waitinglist addfile /path/to/file`
Explanation: Add all the items in the /path/to/file into waiting list. Note that you must make sure each line's item meet the formats like [package_name][version_constraints].
4. `waitinglist clear`
Explanation: Clear all the items in the waiting list.'''
                                result_message = f'Running `{command}`...\n' + msg + '\n'
    
                                return result_message, return_code
                            # 如果是会改变状态的指令执行错误，则回退
                            if not (command.split()[0].strip() in safe_cmd and '>' not in command):
                                self.sandbox.switch_to_pre_image()
                                output_lines.append('The command execution failed, so I have reverted it back to the previous state, which is the environment before running this command.')
                            else:
                                output_lines.append('The command execution failed, please carefully check the output!')
                        result_message = '\n'.join(output_lines)
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
                    # 在持久shell中执行命令
                    self.sandbox.shell.sendline(command)
                    end_time = time.time()
                    self.sandbox.commands[-1]["returncode"] = -1
                    elasped_time = end_time - start_time
                    self.sandbox.commands[-1]["time"] = elasped_time
                    self.sandbox.shell.expect([r'root@.*:.*# '], timeout=timeout)  # 等待bash提示符，带超时

                    # 获取 shell.before 中匹配到的模式之前的输出
                    output = self.sandbox.shell.before.decode('utf-8').strip()
                
                    # 分析输出行，排除发送的命令行和最后的提示符行
                    output_lines = output.split('\r\n')
                    if len(output_lines) > 1:
                        output_lines = output_lines[1:-1]  # 排除发送的命令行

                    result_message = f'Running Edit...\n' + '\n'.join(output_lines)
                    try:
                        return_code = self.get_returncode()
                    except:
                        return_code = 123
                    self.sandbox.commands[-1]['returncode'] = return_code
                    return result_message, return_code

                except pexpect.TIMEOUT:
                    return 'Running Edit...\n' + f"Error: Edit timed out after {timeout} seconds." + '\n', 1
                
            def close(self):
                if self.sandbox.shell:
                    self.sandbox.shell.sendline('exit')
                    self.sandbox.shell.expect(pexpect.EOF)
                    self.sandbox.shell.close(force=True)
                    self.sandbox.shell = None  # 设置shell为None

        return Session(self)

    def stop_container(self):
        if self.container:
            if self.shell and self.shell.isalive():
                self.shell.close(force=True)  # 确保关闭shell
                self.shell = None
            self.container.stop()
            self.container.remove()
            print(f"Container {self.container.short_id} stopped and removed")
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

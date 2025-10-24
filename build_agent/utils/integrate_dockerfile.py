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


import os
import json
import subprocess
import argparse
import shlex
import re

def find_package_version(package_name, dependencies):
    """
    遍历依赖树，查找指定包的实际安装版本
    :param package_name: 要查找的包名
    :param dependencies: 依赖树列表
    :return: 包的实际安装版本或 None 如果未找到
    """
    for package in dependencies:
        if package["key"].lower().replace('-', '_').replace('.', '_') == package_name.lower().replace('-', '_').replace('.', '_'):
            return package["installed_version"]
        # 递归查找子依赖
        sub_version = find_package_version(package_name, package["dependencies"])
        if sub_version:
            return sub_version
    return None

# 用于提取package_name
def extract_package_info(package_with_constraints):
    """
    从形式如 'requests==2.25.1' 的字符串中提取 package_name 和 version_constraints
    """
    pattern = re.compile(r'(?P<package_name>^[^=<>!~]+)(?P<version_constraints>.*)')
    match = pattern.match(package_with_constraints)
    
    if not match:
        raise ValueError(f"Invalid package string: {package_with_constraints}")
    
    package_name = match.group('package_name').strip()
    version_constraints = match.group('version_constraints').strip()
    
    return package_name

# 解析python /home/tools/pip_download.py指令参数
def parse_arguments(command):
    """
    解析包含命令行参数的字符串，提取参数值
    """
    # 使用 shlex.split 分割命令字符串
    args = shlex.split(command)
    # 创建解析器
    parser = argparse.ArgumentParser(description='Install a Python package with pip.')
    parser.add_argument('-p', '--package_name', required=True, type=str, help='The name of the package to install.')
    parser.add_argument('-v', '--version_constraints', type=str, default='', nargs='?', help='The version constraints of the package.')
    # 解析分割后的参数
    parsed_args = parser.parse_args(args[2:])  # 跳过第一个参数（脚本名）
    return parsed_args

# 解析pip install指令参数
def parse_pip_install_arguments(command):
    """
    解析包含 pip install 命令行参数的字符串，提取参数值
    """
    # 使用 shlex.split 分割命令字符串以处理引号和特殊字符
    args = shlex.split(command)

    # 创建解析器
    parser = argparse.ArgumentParser(description='Parse pip install command arguments.')

    # 定义位置参数（包名或者是 requirements）
    parser.add_argument(
        'requirements',
        nargs=argparse.REMAINDER,  # 支持多个包名或要求，获取所有剩余参数
        help='The packages or requirements to install.'
    )

    # 定义常见的 pip install 参数
    parser.add_argument(
        '-r', '--requirement',
        action='append',
        help='Install from the given requirements file. This option can be used multiple times.'
    )
    parser.add_argument(
        '-e', '--editable',
        action='append',
        help='Install a project in editable mode (i.e. setuptools "develop mode"). This option can be used multiple times.'
    )
    parser.add_argument(
        '--no-deps',
        action='store_true',
        help='Do not install package dependencies.'
    )
    parser.add_argument(
        '-t', '--target',
        help='Install packages into <dir>.'
    )
    parser.add_argument(
        '-U', '--upgrade',
        action='store_true',
        help='Upgrade all specified packages to the newest available version.'
    )
    parser.add_argument(
        '--force-reinstall',
        action='store_true',
        help='Reinstall all packages even if they are already up-to-date.'
    )
    parser.add_argument(
        '--no-cache-dir',
        action='store_true',
        help='Disable the cache.'
    )
    parser.add_argument(
        '--user',
        action='store_true',
        help='Install to the Python user install directory for your platform.'
    )
    parser.add_argument(
        '--prefix',
        help='Installation prefix.'
    )
    parser.add_argument(
        '--src',
        help='Directory to check out editable projects into. The default in a virtualenv is "<venv path>/src".'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='count',
        default=0,
        help='Give less output. Option can be used multiple times to increase verbosity.'
    )

    parser.add_argument(
        '-qq', '--quitequiet',
        action='count',
        default=0,
        help='Give less output. Option can be used multiple times to increase verbosity.'
    )
    # 解析分割后的参数
    parsed_args = parser.parse_args(args[1:])  # 跳过第一个参数（pip install）

    return parsed_args


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

# 替换没有版本号的包名成带版本号的函数
def replace_versions(command, pipdeptree_data):
    # print(command)
    args = parse_pip_install_arguments(command)
    new_requirements = []

    for requirement in args.requirements[1:]:
        if '==' not in requirement:
            # 未指定版本号的包名替换为 `<package_name>==<version>`
            package_name = requirement
            package_version = find_package_version(package_name, pipdeptree_data)
            if package_version:
                new_requirements.append(f'{package_name}=={package_version}')
            else:
                new_requirements.append(requirement)
        else:
            new_requirements.append(requirement)
    
    # print(new_requirements)
    # 根据解析的内容重构命令
    if len(new_requirements) > 0:
        new_command = f'pip install {" ".join(new_requirements)}'
    else:
        new_command = 'pip install'
    
    if args.requirement:
        new_command += ' ' + ' '.join(f'-r {req}' for req in args.requirement)
    if args.editable:
        new_command += ' ' + ' '.join(f'-e {edit}' for edit in args.editable)
    if args.no_deps:
        new_command += ' --no-deps'
    if args.target:
        new_command += f' -t {args.target}'
    if args.upgrade:
        new_command += ' -U'
    if args.force_reinstall:
        new_command += ' --force-reinstall'
    if args.no_cache_dir:
        new_command += ' --no-cache-dir'
    if args.user:
        new_command += ' --user'
    if args.prefix:
        new_command += f' --prefix {args.prefix}'
    if args.src:
        new_command += f' --src {args.src}'

    return new_command

def generate_statement(inner_command, pipdeptree_data):
    """
    Convert executed command to Dockerfile RUN statement
    
    Args:
        inner_command: {"command": str, "dir": str, "returncode": int}
        pipdeptree_data: dict (for Python packages, unused for C)
    
    Returns:
        str: "RUN ..." statement or -1 to skip
    """
    command = inner_command['command']
    dir = inner_command['dir'] if 'dir' in inner_command else '/'
    returncode = inner_command['returncode']
    
    # Skip failed commands
    if str(returncode).strip() != '0':
        return -1
    
    action_name = command.split(' ')[0].strip() if command else ''
    
    # Skip read-only commands
    if action_name in safe_cmd and '>' not in command:
        return -1
    
    # Skip analysis tools
    if action_name in ['pipdeptree'] or \
       'runtest.py' in command or \
       'runpipreqs.py' in command or \
       'poetryruntest.py' in command or \
       'generate_diff.py' in command:
        return -1
    
    # ========================================
    # C/C++ Specific Conversions
    # ========================================
    
    # 1. apt_download.py → apt-get install
    if 'apt_download.py' in command:
        import re
        match = re.search(r'-p\s+(\S+)', command)
        if match:
            package = match.group(1)
            return f'RUN apt-get update -qq && apt-get install -y -qq {package}'
        return -1
    
    # 2. apt-get (already correct format)
    if command.startswith('apt-get'):
        return f'RUN {command}'
    
    # 3. configure scripts
    if './configure' in command or './autogen.sh' in command or './bootstrap' in command:
        if command.startswith('cd '):
            return f'RUN {command}'
        # Use actual directory if available, otherwise default to /repo
        if dir != '/':
            return f'RUN cd {dir} && {command}'
        return f'RUN cd /repo && {command}'
    
    # 4. make commands (most common)
    if command.startswith('make') or ' make' in command:
        if command.startswith('cd '):
            return f'RUN {command}'
        # Always include directory context if not root
        if dir != '/' and not command.startswith('cd '):
            return f'RUN cd {dir} && {command}'
        return f'RUN {command}'
    
    # 5. cmake commands
    if 'cmake' in command:
        if command.startswith('cd ') or command.startswith('mkdir'):
            return f'RUN {command}'
        # Always include directory context if not root
        if dir != '/' and not command.startswith('cd '):
            return f'RUN cd {dir} && {command}'
        return f'RUN {command}'
    
    # 6. gcc/g++ direct compilation
    if action_name in ['gcc', 'g++', 'clang', 'clang++']:
        if dir != '/' and not command.startswith('cd '):
            return f'RUN cd {dir} && {command}'
        return f'RUN {command}'
    
    # 7. Environment variables
    if action_name == 'export':
        var_assignment = command.replace('export ', '')
        return f'ENV {var_assignment}'
    
    # 8. Change base image (rare)
    if action_name == 'change_base_image':
        return f'FROM {command.split(" ")[1].strip()}'
    
    # 9. Clear configuration (reset)
    if action_name == 'clear_configuration':
        return 'FROM gcr.io/oss-fuzz-base/base-builder'
    
    # ========================================
    # Python (legacy, keep for compatibility)
    # ========================================
    
    if command.startswith('python /home/tools/pip_download.py'):
        args = parse_arguments(command)
        package_name = args.package_name
        package_version = find_package_version(package_name, pipdeptree_data)
        if package_version:
            return f'RUN pip install {package_name}=={package_version}'
        return -1
    
    if command.startswith('pip install'):
        if dir != '/':
            return f'RUN cd {dir} && {replace_versions(command, pipdeptree_data)}'
        return f'RUN {replace_versions(command, pipdeptree_data)}'
    
    # ========================================
    # Generic commands
    # ========================================
    
    # Already has cd in command
    if command.startswith('cd '):
        return f'RUN {command}'
    
    # Add cd if needed
    if dir != '/' and dir != '/src':
        return f'RUN cd {dir} && {command}'
    
    # Default: as-is
    return f'RUN {command}'

# root_path must be absolute path
def integrate_dockerfile(root_path):
    dockerfile = list()
    root_path = os.path.normpath(root_path)
    author_name = root_path.split('/')[-2]
    repo_name = root_path.split('/')[-1]
    # C 전용 이미지 사용
    base_image_st = 'FROM gcr.io/oss-fuzz-base/base-builder'
    workdir_st = f'WORKDIR /'
    # C 빌드 도구는 base-builder에 이미 포함됨
    pre_download = '# C build tools already included in base-builder'
    
    # Note: search_patch and code_edit.py are legacy from Python version
    # For C-only projects, these files don't exist and aren't needed
    # Removed: COPY search_patch /search_patch
    # Removed: COPY code_edit.py /code_edit.py
    
    # USE COPY instead of git clone to avoid network issues during Dockerfile build
    # The repo is already cloned locally in utils/repo/{author_name}/{repo_name}/repo
    # Path is relative to build context (will be set to project root in main.py)
    copy_repo_st = f'COPY utils/repo/{author_name}/{repo_name}/repo /repo'
    git_save_st = 'RUN git config --global --add safe.directory /repo'
    with open(f'{root_path}/sha.txt', 'r') as r1:
        sha = r1.read().strip()
    checkout_st = f'RUN cd /repo && git checkout {sha}'
    container_run_set = list()
    outer_command = list()
    pip_st = ""
    if not (os.path.exists(f'{root_path}/inner_commands.json')):
        subprocess.run('touch ERROR', cwd=root_path, shell=True)
    with open(f'{root_path}/inner_commands.json', 'r') as r1:
        commands_data = json.load(r1)
    # C 프로젝트는 pipdeptree.json 불필요
    pipdeptree_data = {}
    if os.path.exists(f'{root_path}/pipdeptree.json'):
        with open(f'{root_path}/pipdeptree.json', 'r') as r2:
            pipdeptree_data = json.load(r2)
    diff_no = 1
    for command in commands_data:
        res = generate_statement(command, pipdeptree_data)
        if res == -1:
            continue
        # 修改base镜像，清空container_run_set
        if res.startswith('FROM'):
            base_image_st = res
            container_run_set = list()
        elif command['command'].startswith('python /home/tools/code_edit.py'):
            if diff_no == 1:
                container_run_set.append(f'RUN cd /repo && git apply --reject /patch/patch_{diff_no}.diff --allow-empty')
            else:
                container_run_set.append(f'RUN cd /repo && git apply -R --reject /patch/patch_{diff_no - 1}.diff --allow-empty')
                container_run_set.append(f'RUN cd /repo && git apply --reject /patch/patch_{diff_no}.diff --allow-empty')
            diff_no += 1
        else:
            container_run_set.append(res)
    
    # 组合最后的顺序
    dockerfile.append(base_image_st)
    dockerfile.append(workdir_st)
    # Note: Legacy COPY statements removed (search_patch, code_edit.py not needed for C projects)
    dockerfile.extend(pip_st.splitlines())
    dockerfile.extend(pre_download.splitlines())
    dockerfile.append(copy_repo_st)  # COPY local repo instead of git clone
    dockerfile.append(git_save_st)
    dockerfile.append(checkout_st)  # 🆕 CRITICAL: Checkout specific commit SHA
    dockerfile.extend(container_run_set)
    with open(f'{root_path}/Dockerfile', 'w') as w1:
        w1.write('\n'.join(dockerfile))

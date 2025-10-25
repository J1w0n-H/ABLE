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

import os, sys, json
import subprocess
from agents.agent import Agent
from utils.llm import get_llm_response
from utils.agent_util import safe_cmd, extract_commands, append_trajectory, TIME_OUT_LABEL, extract_diffs, save_diff_description, DIFF_FENCE, BASH_FENCE, INIT_PROMPT, EDIT_PROMPT, HEAD, DIVIDER, UPDATED
from utils.tools_config import Tools
from utils.split_cmd import split_cmd_statements
import re
import time

def res_truncate(text):
    keywords = ['''waitinglist command usage error, the following command formats are leagal:
1. `waitinglist add -p package_name1 -t apt`
Explanation: Add package_name1 into waiting list(using apt-get), no version means install the latest available version by default.
2. `waitinglist addfile /path/to/file`
Explanation: Add all the items in the /path/to/file into waiting list. Note that you must make sure each line contains a valid package name.
3. `waitinglist clear`
Explanation: Clear all the items in the waiting list.''', 
        'If you have multiple elements to add to the waitinglist, you can use && to connect multiple `waitinglist add` statements and surround them with ```bash and ```. Please make sure to write the complete statements; we will only recognize complete statements. Do not use ellipses or other incomplete forms.',
        '''conflictlist command usage error, the following command formats are legal:
1. `conflictlist solve`
Explanation: The standalone `conflictlist solve` command means not to impose any version constraints, i.e., to default to downloading the latest version of the library.
2. `conflictlist solve -u`
Explanation: Adding -u indicates giving up the constraints in the conflict list while still retaining the constraints in the waiting list.
3. `conflictlist clear`
Explanation: Clear all the items in the conflict list.''',
        'If you have multiple elements to remove from the conflict list, you can use && to connect multiple `conflictlist solve` statements and surround them with ```bash and ```. Please make sure to write the complete statements; we will only recognize complete statements. Do not use ellipses or other incomplete forms.'
        ]
    # 遍历每个关键词，找到其在文本中出现的位置
    all_positions = {}
    for keyword in keywords:
        positions = [i for i in range(len(text)) if text.startswith(keyword, i)]
        if len(positions) > 1:
            all_positions[keyword] = positions

    if not all_positions:
        return text

    # 从결과文本开始，处理每个关键词的位置，保留最后一个
    new_text = text
    keywords_to_remove = sorted(all_positions.items(), key=lambda item: item[1][-1], reverse=True)

    for keyword, positions in keywords_to_remove:
        last_position = positions[-1]
        before_last_position = new_text[:last_position].replace(keyword, "", len(positions) - 1)
        after_last_position = new_text[last_position:]
        new_text = before_last_position + after_last_position

    return new_text

class Configuration(Agent):
    def __init__(self, sandbox, image_name, full_name, root_dir, max_turn=70):
        self.model = "gpt-4o-2024-05-13"
        # self.model = "aws_claude35_sonnet"
        self.root_dir = root_dir
        self.max_turn = max_turn
        self.sandbox = sandbox
        self.sandbox_session = self.sandbox.get_session()
        self.full_name = full_name
        self.tool_lib = [
            Tools.waiting_list_add,
            Tools.waiting_list_add_file,
            Tools.waiting_list_clear,
            Tools.conflict_solve_u,
            Tools.conflict_clear,
            Tools.conflict_list_show,
            Tools.waiting_list_show,
            Tools.download,
            Tools.runtest,
            Tools.clear_configuration,
        ]
        self.image_name = image_name
        self.outer_commands = list()
        tools_list = ""
        for tool in self.tool_lib:
            tools_list += f"{tool.value['command']} # {tool.value['description']}\n"
        self.init_prompt = f"""\
╔══════════════════════════════════════════════════════════════════════════╗
║                C/C++ BUILD ENVIRONMENT CONFIGURATION                     ║
╚══════════════════════════════════════════════════════════════════════════╝

## 🎯 YOUR MISSION
Configure and build a C/C++ project in Docker ({self.image_name}).
Basic tools available: gcc, g++, make, cmake, clang
SUCCESS = Build completes + runtest passes with "Congratulations!"

╔══════════════════════════════════════════════════════════════════════════╗
║              💡 SUGGESTED FIXES - TIERED RESPONSE SYSTEM                  ║
╚══════════════════════════════════════════════════════════════════════════╝

**IF YOU SEE SUGGESTED FIXES IN ANY OBSERVATION, THEY ARE TIERED:**

### 🔴 TIER 1: MANDATORY (shown with ⛔)
**Error 127 (command not found) and Missing Headers**

When you see:
```
🔴🔴🔴 STOP! EXECUTE THIS EXACT COMMAND 🔴🔴🔴

⛔ COPY AND RUN THIS EXACT COMMAND:

   apt-get install texinfo && make -j4
```

**YOU MUST:**
1. ⛔ COPY the command shown EXACTLY (with &&)
2. ⛔ RUN it in one action
3. ⛔ DO NOTHING ELSE

**WHY ONE COMMAND?**
- Combines install + retry in single step
- No chance to forget the retry
- Guaranteed correct sequence

**EXAMPLE:**
```
Last command failed: make -j4
Error 127: makeinfo not found

You'll see:
⛔ COPY AND RUN THIS EXACT COMMAND:
   apt-get install texinfo && make -j4

Just copy-paste and run it! Done! ✅
```

**DON'T:**
- ❌ Split into two turns (install, then retry)
- ❌ Run configure instead
- ❌ Modify the command

### 🟡 TIER 2: RECOMMENDED (shown with ✅)
**Library Dependencies and Configure Errors**

You SHOULD:
- Follow as first attempt (usually correct)
- If it fails, then try alternatives

### 🟢 TIER 3: ADVISORY (shown with 💡)
**Complex Build Issues**

You MAY:
- Consider as hints
- Analyze and choose best approach

---

WORK PROCESS:
1. **Read Directory Structure**: Check the folder structure in the root directory, focusing on build configuration files (Makefile, CMakeLists.txt, configure, etc.).
2. **Check the configuration files in the root directory**: Read build configuration files such as: `Makefile`, `CMakeLists.txt`, `configure.ac`, `configure.sh`, `.github` folder for CI configurations, `README.md` for build instructions, etc.
    **IMPORTANT - Smart File Reading to Avoid Token Overflow**:
    - ✅ **Use grep for finding patterns** (fastest): `grep -n "AC_CHECK_LIB" configure.ac`, `grep -A5 -B5 "pattern" file`
    - ✅ **Use sed for specific ranges** when you know line numbers: `sed -n '100,200p' file` (lines 100-200)
    - ✅ **Use cat for complete file** if small (<200 lines) or you need everything: `cat Makefile`, `cat config.txt`
    - ⚠️ **AVOID incremental reading**: Do NOT do head -50, then head -100, then head -150... This wastes turns!
    
    **🆕 LONG OUTPUT HANDLING**:
    If command output exceeds 500 lines, it will be saved to `/tmp/last_command_output.txt`
    You'll see:
    ```
    ⚠️  Output too long (2847 lines) - saved to /tmp/last_command_output.txt
    
    💡 Use these commands to inspect:
       - tail -100 /tmp/last_command_output.txt
       - grep 'Error 127' /tmp/last_command_output.txt
       - grep -i 'fatal error' /tmp/last_command_output.txt
    ```
    
    **HOW TO USE:**
    - Don't panic! The full output is saved
    - Use grep/tail to find what you need
    - Focus on error messages (usually in last 100 lines)
2.5 **Understand build requirements**: Identify which build system is used (CMake, autoconf, or Makefile) to determine the correct build sequence.
3. **Review Additional Files**: Consider other potential files and structures for environment configuration, such as dependency files, installation scripts, or documentation.
4. **Analyze build dependencies**: Based on the observed structure in the root directory, determine the necessary system packages and libraries:
    a. CMake Detected: If CMakeLists.txt exists, check for find_package() or pkg_check_modules() calls to identify required libraries.
    b. Makefile Detected: If Makefile exists, check for library dependencies (usually specified with -l flags).
    c. Configure Script: If configure or configure.ac exists, examine for AC_CHECK_LIB or PKG_CHECK_MODULES to find dependencies.
    d. README/INSTALL: Check documentation for explicit dependency lists.
5. **Install system dependencies**: Use apt-get to install required libraries and development packages:
    - For each library dependency, install the corresponding -dev package (e.g., libssl-dev, libcurl4-openssl-dev)
    - Install build tools if needed (autoconf, automake, libtool, pkg-config, etc.)
    - Use `apt-get update -qq && apt-get install -y -qq <packages>` for quiet installation
6. ⚠️ **MANDATORY: Run build configuration** (DO NOT SKIP THIS STEP!):
    - If configure exists: You MUST run `cd /repo && ./configure`
    - If configure.ac exists but configure does not: Try `./autogen.sh` or `./bootstrap` first, then `./configure`
    - If CMakeLists.txt exists: You MUST run `mkdir -p /repo/build && cd /repo/build && cmake .. -DCMAKE_BUILD_TYPE=Release`
    - If build.sh or compile.sh exists: Check and run the build script: `chmod +x build.sh && ./build.sh`
    - Check for any missing dependencies reported by configure/cmake
7. ⚠️ **MANDATORY: Build the project** (DO NOT SKIP THIS STEP!):
    - For autoconf projects: You MUST run `make -j4` in /repo (parallel build for speed)
    - For CMake projects: You MUST run `make -j4` in /repo/build (parallel build for speed)
    - Fix any compilation errors by installing missing dependencies
    - This step compiles source code into executables and libraries
    - Note: -j4 enables parallel compilation with 4 jobs; adjust based on available CPU cores
8. **Error Handling**: After attempting to build or test, handle error messages:
    - Missing header files: Install corresponding -dev packages (e.g., fatal error: openssl/ssl.h → install libssl-dev)
    - Missing libraries: Install library packages (e.g., cannot find -lz → install zlib1g-dev)
    - **⚠️ Error 127 or Missing Headers**: Follow TIER 1 instructions at top of prompt (MANDATORY!)
    - **⚠️ Other errors**: Follow TIER 2/3 suggestions or analyze yourself
    You can make use of the following tools:
    a. `apt-cache search <keyword>`: Search for available packages
    b. `apt-cache show <package>`: Show package information
    c. `dpkg -L <package>`: List files installed by a package
    d. `pkg-config --list-all`: List all packages known to pkg-config
    e. `pkg-config --cflags --libs <package>`: Show compile and link flags for a package
    f. `apt-get update -qq && apt-get install -y -qq <package>`: Install system packages quietly
    g. `export <variable>=<value>`: Set environment variables (CC, CXX, CFLAGS, LDFLAGS, etc.)
    h. `ldconfig`: Update shared library cache if needed
    i. You can use the `--help` or `man` command to view detailed usage instructions for various tools
    j. You may also use other commands that are not listed here, including built-in Bash commands and other system commands.
    *Note*: Always consider the potential impact of each command on the system. Aim to achieve the best results with minimal changes.
    *Note*: For missing headers or libraries, first check if they are part of the project itself (local includes) before installing external packages.
    *Note*: Do not use external download tools like `git clone` or `wget` to download a large number of files directly in the /repo folder (or its subdirectories) to avoid causing significant changes to the original repository.
    *Note*: You can use `clear_configuration` command to restore the Docker environment to its initial clean state if needed.
    *Note*: runtest should be executed AFTER completing the build. It verifies the build and runs tests, but does NOT build the project itself.
    *CRITICAL*: download command behavior:
        • download processes ALL packages in waiting list AT ONCE
        • Call download ONLY ONCE after adding all needed packages
        • Do NOT call download multiple times in a row - this wastes time!
        • After download completes, the waiting list becomes EMPTY
        • If download says "WAITING LIST IS EMPTY", do NOT call it again
        • Only call download again if you add NEW packages to waiting list
        • Typical workflow: (1) waitinglist add -p pkg1 -t apt, (2) waitinglist add -p pkg2 -t apt, (3) download ONCE
If you encounter compilation errors or missing dependencies, you can consider two solutions. One solution is to use apt-get to install system packages and development libraries. The other solution is to check for local dependencies in the repository; if local dependencies are available, you can set appropriate environment variables (PATH, LD_LIBRARY_PATH, CFLAGS, LDFLAGS, etc.) to resolve the issue.
**IMPORTANT**: For most cases, use **direct apt-get install** instead of waiting list:
```bash
apt-get install <package>  # RECOMMENDED (fast, reliable)
```
Only use waiting list if you need to batch-install many packages at once.
In each round of the conversation, we will inform you of the commands that have been correctly executed and have changed the state of the current Docker container. Please reflect on each round's Observation in relation to the current state of the Docker container and decide the subsequent Action.
**CRITICAL**: All commands must be single-line using && (no if/then/fi, no backslash \\, no multi-line). See CRITICAL RULES below for details.

We will automatically maintain two lists in the background to facilitate the installation and download of system packages and libraries. These are:
1. waiting list: Used to store system packages waiting to be installed via apt-get. You can use `waitinglist show` to show all items in it.
2. conflict list: Used to store elements with the same name as those in the waiting list but with inconsistent constraints. You can use `conflictlist show` to show all items in it.
*Note*: you only need to follow the prompts to complete operations on these lists during the running process and can only manipulate them using the provided commands.
*Note*: Before operating waiting list, conflict list, or download commands, you can use waitinglist show or conflictlist show to observe their structure each time.

{INIT_PROMPT}
You are now in the Docker environment of {self.image_name}. Please perform all operations within this environment.
CLI TOOLS: You can call CLI tools in  {BASH_FENCE[0]} ... {BASH_FENCE[1]} block as Action with a Thought. like:
### Thought: I need to understand the structure of the root directory.
### Action:
{BASH_FENCE[0]}
ls /repo
{BASH_FENCE[1]}

For another example:
### Thought: I need to read the README.md file.
### Action:
{BASH_FENCE[0]}
cat README.md
{BASH_FENCE[1]}

{EDIT_PROMPT}
*Note*: Do not make extensive changes to the existing files in the /repo folder. You may only make appropriate and necessary changes to the original repository files (e.g., when there are actual errors or tests that cannot be run).
*Very Important Note*: Passing tests by modifying testing functions is not allowed, and you should figure out how to make the current test functions run successfully!!!
In addition to typical bash commands, we also provide the following commands that can be used, you can use them flexibly if needed:
{tools_list}

╔══════════════════════════════════════════════════════════════════════════╗
║                          ⚠️  CRITICAL RULES ⚠️                           ║
╚══════════════════════════════════════════════════════════════════════════╝

1. **YOUR TASK**: Configure C/C++ build environment (NOT answer questions!)
   → Follow workflow above → Pass runtest

2. **BUILD BEFORE RUNTEST** (Most Important!)
   ❌ WRONG: dependencies → runtest (skips build!)
   ✅ RIGHT: dependencies → configure → make → runtest
   → runtest does NOT build - it only verifies!

3. **DO NOT MODIFY TEST FILES**
   ❌ WRONG: Edit test_*.c to make tests pass
   ✅ RIGHT: Fix actual code or install missing dependencies

4. **ONE-LINE COMMANDS** (CRITICAL!)
   ❌ WRONG: Multi-line if/then/fi (causes syntax errors!)
```bash
   if [ -f file ]; then
     cmd
   fi
```
   ✅ RIGHT: Single line with &&
```bash
   test -f file && cmd || true
   ```
   ❌ WRONG: Backslash continuation
   ✅ RIGHT: Use && to chain: `cd /repo && ./configure && make -j4`

5. **PRESERVE SOURCE FILES**
   → Only modify when absolutely necessary
   → Never delete test files or build scripts
   → Prefer: install packages, set env vars

6. **NO INTERACTIVE SHELLS**
   ❌ FORBIDDEN: hatch shell, tmux, interactive prompts
   ✅ ALLOWED: Direct bash commands only
"""
    def show_init_prompt(self):
        print(self.init_prompt)
    
    def get_max_turn(self):
        return self.max_turn

    def run(self, project_path, trajectory, waiting_list, conflict_list):
        print('************** configuration **************')
        print(self.init_prompt)
        start_time0 = time.time()
        self.messages = []
        if "gpt" in self.model:
            system_message = {"role": "system", "content": self.init_prompt}
            self.messages.append(system_message)
            user_message = {"role": "user", "content": f"[Project root Path]: /repo"}
            self.messages.append(user_message)
        else:
            assert "claude" in self.model
            claude_prompt = f"{self.init_prompt} \n[Project root Path]: /repo"
            user_message = {"role": "user", "content": claude_prompt}
            self.messages.append(user_message)

        turn = 0
        cost_tokens = 0
        diff_no = 1
        def manage_token_usage(messages, max_tokens=30000):
            """
            在消息列表超过Token限制时，从最老的消息开始删除，直到总Token数量低于max_tokens。
            使用切片操作来管理Token使用。
            Max tokens set to 30000 to match LLM context limit.
            """
            total_tokens = sum(len(str(message)) for message in messages)
            if total_tokens <= max_tokens:
                return messages  # 如果总Token数不超过限制，返回原始消息列表

            # 计算应保留的消息数量
            new_messages = messages[:]
            while sum(len(str(message)) for message in new_messages) > max_tokens:
                # new_messages = new_messages[4:]  # 切片删除最老的消息（不是第0个）
                new_messages = new_messages[:4] + new_messages[6:]

            return new_messages
        
        # 传入内部指令，传出所有正确执行的历史指令
        def extract_cmds(inner_commands):
            res_cmd = list()
            for inner_command in inner_commands:
                command = inner_command['command']
                dir = inner_command['dir'] if 'dir' in inner_command else '/'
                returncode = inner_command['returncode']
                action_name = command.split(' ')[0].strip()
                
                # Skip failed commands
                if str(returncode).strip() != '0':
                    continue
                
                # Skip safe commands (double check for safety)
                if action_name in safe_cmd and '>' not in command:
                    continue
                
                # Skip analysis tools
                if command == 'python /home/tools/runtest.py' or command == 'python /home/tools/generate_diff.py' or command == '$pwd$':
                    continue
                
                # Skip clear_configuration (resets history)
                if action_name == 'clear_configuration':
                    res_cmd = list()
                    continue
                
                # Only include commands that actually modify system state
                if dir != '/':
                    res_cmd.append(f'cd {dir} && {command}')
                else:
                    res_cmd.append(command)
            return res_cmd

        while(turn < self.max_turn):
            turn += 1
            finish = False
            GPT_start_time = time.time()
            current_messages = manage_token_usage(self.messages)

            configuration_agent_list, usage = get_llm_response(self.model, current_messages)
            GPT_end_time = time.time()
            GPT_elasped_time = GPT_end_time - GPT_start_time
            self.outer_commands.append({"GPT_time": GPT_elasped_time})
            configuration_agent = configuration_agent_list
            
            # Handle None response (e.g., rate limit, API error)
            if configuration_agent is None:
                print('Error: LLM returned None response. This may be due to rate limits or token overflow.')
                print('Waiting 60 seconds before retrying...')
                time.sleep(60)
                continue
            
            if usage is not None:
                cost_tokens += usage.total_tokens

            # 将模型回答加入记忆
            assistant_message = {"role": "assistant", "content": configuration_agent}
            self.messages.append(assistant_message)
            print('---------------------------')
            print(configuration_agent)
            system_res = '### Observation:\n'
            init_commands = extract_commands(configuration_agent)
            commands = list()
            for ic in init_commands:
                commands.extend(split_cmd_statements(ic))
            diffs = extract_diffs(configuration_agent)
            #如果回答중同时有修改和命령，拒绝
            if len(diffs) != 0 and len(commands) != 0:
                system_res = f"ERROR! Your reply contains both bash block and diff block, which is not accepted. Each round of your reply can only contain one {BASH_FENCE[0]} {BASH_FENCE[1]} block or one {DIFF_FENCE[0]} {DIFF_FENCE[1]} block. Each round of your answers contain only *ONE* action!"
            elif len(commands) != 0: #按顺序执行工具
                for i in range(len(commands)):
                    self.outer_commands.append({"command": commands[i], "returncode": -2, "time": -1})
                    start_time = time.time()
                    vdb = subprocess.run("df -h | grep '/dev/vdb' | awk '{print $5}'", shell=True, capture_output=True, text=True)
                    if vdb.stdout.strip() and '%' in vdb.stdout.strip():
                        usage_percent = float(vdb.stdout.strip().split('%')[0])
                        if usage_percent > 90:
                            print('Warning! The disk /dev/vdb has occupied over 90% memories!')
                            sys.exit(3)
                    
                    # 恢복 초기 상태
                    if commands[i].strip() == 'clear_configuration':
                        try:
                            sandbox = self.sandbox_session.sandbox.clear_configuration()
                            self.sandbox = sandbox
                            self.sandbox_session = self.sandbox.get_session()
                            res = f"You have successfully cleared the docker container configuration and restored it to the initial state."
                            # 내부 명령에 플래그 추가
                            self.sandbox.commands.append({"command": f'clear_configuration', "returncode": 0, "time": -1})
                            print(res)
                            system_res += res
                        except Exception as e:
                            res = f"Error to clear the docker container configuration, the error messages are: {e}"
                            print(res)
                            self.outer_commands[-1]["returncode"] = 1
                            system_res += res
                        end_time = time.time()
                        elasped_time = end_time - start_time
                        self.outer_commands[-1]["time"] = elasped_time
                        self.outer_commands[-1]["returncode"] = 0
                        if self.sandbox.commands[-1]['command'] == f'clear_configuration':
                            self.sandbox.commands[-1]["time"] = elasped_time
                        continue

                    sandbox_res, return_code =  self.sandbox_session.execute(commands[i], waiting_list, conflict_list)
                    sandbox_res = res_truncate(sandbox_res)
                    system_res += sandbox_res
                    if return_code != 'unknown':
                        system_res += f'\n`{commands[i]}` executes with returncode: {return_code}\n'
                    end_time = time.time()
                    elasped_time = end_time - start_time
                    self.outer_commands[-1]["time"] = elasped_time
                    self.outer_commands[-1]["returncode"] = 0
                    #重置session
                    if TIME_OUT_LABEL in sandbox_res:
                        self.sandbox_session = self.sandbox.get_session()
                        self.outer_commands[-1]["returncode"] = 1
                    success_check = 'Congratulations, you have successfully configured the environment!' in sandbox_res
                    runtest_check = '# This is $runtest.py$' not in sandbox_res
                    
                    if success_check and runtest_check:
                        # ========================================
                        # SUCCESS: Save final state without rollback
                        # ========================================
                        print("\n" + "="*70)
                        print("🎉 BUILD SUCCESS!")
                        print("="*70)
                        
                        try:
                            # Generate package list from waiting_list instead of dpkg -l
                            installed_packages = []
                            for item in waiting_list.items:
                                if item.tool.strip().lower() == 'apt':
                                    installed_packages.append(f"{item.package_name} {item.version_constraints if item.version_constraints else 'latest'}")
                            
                            dpkg_list = '\n'.join(installed_packages) if installed_packages else "No packages installed via apt"
                            dpkg_list_return_code = 0
                        except Exception as e:
                            dpkg_list = "Error generating package list"
                            dpkg_list_return_code = -1
                        
                        try:
                            generate_diff, generate_diff_return_code = self.sandbox_session.execute('generate_diff', waiting_list, conflict_list)
                        except Exception as e:
                            generate_diff_return_code = -1

                        if len(generate_diff.strip()) > 0 and generate_diff_return_code == 0:
                            if not os.path.exists(f'{self.root_dir}/output/{self.full_name}/patch'):
                                os.system(f'mkdir {self.root_dir}/output/{self.full_name}/patch')
                            with open(f'{self.root_dir}/output/{self.full_name}/patch/final_patch.diff', 'w') as w0:
                                w0.write(generate_diff)
                        if dpkg_list_return_code == 0:
                            with open(f'{self.root_dir}/output/{self.full_name}/dpkg_list.txt', 'w') as w1:
                                w1.write(dpkg_list)

                        print(sandbox_res)
                        with open(f'{self.root_dir}/output/{self.full_name}/test.txt', 'w') as w3:
                            w3.write('\n'.join(sandbox_res.splitlines()[1:]))
                        finish = True
                        break
                if finish:
                    break
            elif len(diffs) != 0:
                if diffs.split('<<<<<<< SEARCH')[0].split('/')[-1].strip().startswith('test_') or diffs.split('<<<<<<< SEARCH')[0].split('/')[-1].strip().endswith('_test.py'):
                    self.outer_commands.append({"diff": diffs, "returncode": -2, "time": -1})
                    system_res += 'Running Edit...\n' + f"You are trying to modify file {diffs.split('<<<<<<< SEARCH')[0].split('/')[-1].strip()}, but we require that you should not modify the testing files. Please consider alternative solutions." + '\n'
                else:
                    self.outer_commands.append({"diff": diffs, "returncode": -2, "time": -1})
                    start_time = time.time()
                    tmp_name = save_diff_description(diffs)
                    sandbox_res, return_code =  self.sandbox_session.edit(tmp_name, project_path)
                    end_time = time.time()
                    elasped_time = end_time - start_time
                    self.outer_commands[-1]["returncode"] = 0
                    self.outer_commands[-1]["time"] = elasped_time
                    if return_code == 0:
                        try:
                            generate_diff, generate_diff_return_code = self.sandbox_session.execute('generate_diff', waiting_list, conflict_list)
                        except Exception as e:
                            print(f'Generate diff wrong: {e}!')
                        # if len(generate_diff.strip()) > 0 and generate_diff_return_code == 0:
                        if not os.path.exists(f'{self.root_dir}/output/{self.full_name}/patch'):
                            os.system(f'mkdir {self.root_dir}/output/{self.full_name}/patch')
                        with open(f'{self.root_dir}/output/{self.full_name}/patch/patch_{diff_no}.diff', 'w') as w0:
                            w0.write(generate_diff + '\n')
                        diff_no += 1
                    system_res += sandbox_res
                    #重置session
                    if TIME_OUT_LABEL in sandbox_res:
                        self.sandbox_session =  self.sandbox.get_session()
                    if HEAD not in diffs or DIVIDER not in diffs or UPDATED not in diffs:
                        self.outer_commands[-1]["returncode"] = 1
                        system_res += f"""#### Your patch is incomplete with {HEAD} or {DIVIDER} or {UPDATED} missing! ####            
The edit format is as follows: 

{DIFF_FENCE[0]}
/absolute/path/of/target.py
{HEAD}
    exact copy of old line(s) you would like to change
{DIVIDER}
    new line(s) to replace
{UPDATED}
"""
            else:
                self.outer_commands[-1]["returncode"] = 2
                system_res += "ERROR! Your reply does not contain valid block or final answer."
            
            current_directory, return_code = self.sandbox_session.execute('$pwd$', waiting_list, conflict_list)
            current_directory = '\n[Current directory]:\n' + current_directory + '\n'
            system_res += current_directory
            system_res += f'You are currently in a [{self.image_name}] container.\n'
            reminder = f"\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left to complete the task."
            system_res += reminder
            success_cmds = extract_cmds(self.sandbox.commands)

            if len(success_cmds) > 0:
                appendix = '\nThe container has successfully executed the following commands in order. Please refer to the execution history, reflect, and decide the subsequent actions. Remember, your ultimate goal is to pass the tests by executing `runtest`.\n' + \
                    '\n'.join(success_cmds)
            else:
                appendix = '\nThe container remains in its original state.'
            pattern = r'python\s+/home/tools/apt_download.py\s+-p\s+(\S+)'

            replacement = r'apt-get install \1'
            appendix = re.sub(pattern, replacement, appendix)
            
            system_res += appendix
            if "gpt" in self.model:
                system_message = {"role": "system", "content": system_res}
            else:
                system_message = {"role": "user", "content": system_res}
            self.messages.append(system_message)
            with open(f'{self.root_dir}/output/{self.full_name}/outer_commands.json', 'w') as w1:
                w1.write(json.dumps(self.outer_commands, indent=4))
            with open(f'{self.root_dir}/output/{self.full_name}/inner_commands.json', 'w') as w1:
                w1.write(json.dumps(self.sandbox.commands, indent=4))
            print(system_res)

            try:
                generate_diff, generate_diff_return_code = self.sandbox_session.execute('generate_diff', waiting_list, conflict_list)
            except:
                generate_diff_return_code = -1

            if len(generate_diff.strip()) > 0 and generate_diff_return_code == 0:
                if not os.path.exists(f'{self.root_dir}/output/{self.full_name}/patch'):
                    os.system(f'mkdir {self.root_dir}/output/{self.full_name}/patch')
                with open(f'{self.root_dir}/output/{self.full_name}/patch/final_patch.diff', 'w') as w0:
                    w0.write(generate_diff)
        
        append_trajectory(trajectory, self.messages, 'configuration')
        end_time0 = time.time()
        cost_time = end_time0 - start_time0
        trajectory.append({'agent': "configuration", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
        self.sandbox_session.close()
        return trajectory, self.outer_commands
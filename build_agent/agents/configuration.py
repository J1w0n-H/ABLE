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

# Support both direct execution and package import
try:
    from .agent import Agent
    from ..config import Config
    from ..utils.llm import get_llm_response
    from ..utils.agent_util import safe_cmd, extract_commands, append_trajectory, TIME_OUT_LABEL, extract_diffs, save_diff_description, DIFF_FENCE, BASH_FENCE, INIT_PROMPT, EDIT_PROMPT, HEAD, DIVIDER, UPDATED
    from ..utils.tools_config import Tools
    from ..utils.split_cmd import split_cmd_statements
except ImportError:
    from agents.agent import Agent
    from config import Config
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
    def __init__(self, sandbox, image_name, full_name, root_dir, max_turn=None, output_root=None):
        self.model = Config.LLM_MODEL
        self.root_dir = root_dir
        self.output_root = output_root if output_root else Config.OUTPUT_ROOT
        self.max_turn = max_turn if max_turn else Config.MAX_TURN
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
║                    📋 WORK PROCESS (4 STEPS)                             ║
╚══════════════════════════════════════════════════════════════════════════╝

**OVERALL FLOW:**
STEP1. **Scan** → Check build system type + read documentation
STEP2. **Build** → Pick ONE build command and run it 
STEP3. **Fix errors** → Read error messages, install what's missing
   - If same error 2-3 times → Check INSTALL/README from step 1
STEP4. **Verify** → Run `python /home/tools/runtest.py` when build succeeds

**🚨 COMMAND REPETITION RULES (CRITICAL!):**
1. **NEVER** run the exact same command twice in a row
2. If a command succeeds → Move on to the next step
3. If a command fails → Analyze WHY, then try a DIFFERENT command
4. If chained command partially succeeds (e.g., `pip3 install meson && meson setup build` → pip3 ✓, meson ✗) → DON'T re-run pip3!

---

**STEP 1: Quick scan**
```bash
ls -1 /repo | grep -iE "CMakeLists.txt|Makefile|configure|meson.build|WORKSPACE|build.sh" && (grep -iR --include="*README*" --include="*INSTALL*" --include="*BUILD*" -E "(cmake|make|bazel|configure|meson|gcc|clang)" /repo || echo "No build instructions found in README/INSTALL files")
```
→ Read the installation documentation (CMakeLists.txt|Makefile|configure|meson.build|WORKSPACE|build.sh) briefly to understand the correct build process before proceeding.

**STEP 2: Build** (choose by what files exist)
- `configure` exists → `cd /repo && ./configure` (then `make -j$(nproc)` if successful)
- `configure.ac` but NO `configure` → Need autoreconf first:
  ```bash
  apt-get install -y autoconf automake libtool && cd /repo && autoreconf -fi && ./configure && make -j$(nproc)
  ```
- `CMakeLists.txt` → `cmake -S /repo -B /repo/build -DCMAKE_BUILD_TYPE=Release && make -C /repo/build -j$(nproc)`
- `meson.build` → `pip3 install meson && export PATH=$PATH:/usr/local/bin && cd /repo && meson setup build && ninja -C build`
- `.bazelversion`/`WORKSPACE` → `cd /repo && bazel sync --configure && bazel build //... && bazel test //...`
  - **CRITICAL**: `cd /repo` first! `bazel sync` fetches external deps!
- `Makefile` only → `make -C /repo -j$(nproc)`
**STEP 3: If build FAILS - Analyze and Fix**

**Read the output CAREFULLY:**
- 📋 **RECENT COMMAND HISTORY** = Recent commands that have been executed and their results(Don't repeat)
- 💡 **DETECTED ISSUES** = Pattern-based hints (what's likely missing)
- 🚨 **ERROR MESSAGES** = Actual error output (what failed)
- ⚠️ **CRITICAL**: NEVER run the exact same command twice! If it succeeded once, move on. If it failed, try something DIFFERENT 
**Common patterns:**
- "Command 'X' not found" → `apt-cache search X`, then install package
- "Missing header 'X.h'" → `apt-cache search X.h`, then install -dev package
- "Undefined autoconf macros" → `apt-get install -y autoconf-archive`
- "Config cache conflict" → `find /repo -name 'config.cache' -delete && ./configure`
- "Ninja not found" → `apt-get install -y ninja-build`

**Key principles:**
- **Read BOTH sections** - hints guide you, errors confirm the issue
- **Use apt-cache search** when you're unsure which package provides what
- **Only retry the failed step** - don't restart from scratch!
- **Use && chaining** - install → retry in one command

---

╔══════════════════════════════════════════════════════════════════════════╗
║    🎯 MISSION: Configure C/C++ Build + Pass ABLE's Test Verification    ║
╚══════════════════════════════════════════════════════════════════════════╝

**SUCCESS CRITERIA:** 
Execute `python /home/tools/runtest.py` after successful build.
It will show "Congratulations, you have successfully configured the environment!" on success.
---

**KEY TOOLS:**
- `apt-cache search <keyword>` - Find packages
- `apt-get install -y <package>` - Install packages (RECOMMENDED)
- `pkg-config --cflags --libs <pkg>` - Get compile/link flags
- Use `--help` or `man` for other tools

**PACKAGE INSTALLATION:**
Use direct `apt-get install <package>` for best results. Waiting list is available but slower (see `{tools_list}` below for commands).

{INIT_PROMPT}
You are now in the Docker environment of {self.image_name}. Please perform all operations within this environment.
CLI TOOLS: You can call CLI tools in  {BASH_FENCE[0]} ... {BASH_FENCE[1]} block as Action with a Thought.

**Example 1 - First scan:**
### Thought: Since the prompt says to scan first, I need to identify what build system files exist.
### Action:
{BASH_FENCE[0]}
ls -1 /repo | grep -iE "CMakeLists.txt|Makefile|configure|meson.build"
{BASH_FENCE[1]}

**Example 2 - After seeing an error:**
### Thought: Since the error message says "Could not detect Ninja", and the output shows "Successfully installed meson" and "Build targets in project: 46", I can see that meson setup succeeded. Only ninja is missing. So I'll install ninja-build and retry only the ninja step.
### Action:
{BASH_FENCE[0]}
apt-get install -y ninja-build && cd /repo && ninja -C build
{BASH_FENCE[1]}

**Example 3 - WRONG! (Command repetition):**
### Thought: Since the package installation succeeded, let me install it again to make sure.
### Action:
{BASH_FENCE[0]}
apt-get install -y autoconf-archive  # ❌ WRONG! Already succeeded once!
{BASH_FENCE[1]}

**Example 3 - CORRECT! (No repetition):**
### Thought: Since the output shows "autoconf-archive is already the newest version", the package is installed. Now I should move to the next step: configure.
### Action:
{BASH_FENCE[0]}
cd /repo && ./configure
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
   
   **🎯 SUCCESS = See this message from `runtest`:**
   ```
   "Congratulations, you have successfully configured the environment!"
   ```
   
   **Workflow**: dependencies → build → **`runtest`** → "Congratulations!"
   
   ❌ **NOT complete**: `make` succeeds, `meson test` passes, `bazel test` OK
   ✅ **IS complete**: `runtest` shows "Congratulations!"

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

6. **EVERY THOUGHT MUST START WITH "Since"** (CRITICAL!)
   ❌ WRONG: "### Thought: The configure script failed..."
   ✅ RIGHT: "### Thought: Since the error shows 'winscard.h is required', ..."
   → ALWAYS quote what you observed from the output
   → Then explain your reasoning based on that observation

7. **NO INTERACTIVE SHELLS**
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
            When message list exceeds token limit, delete from the oldest messages
            until total token count is below max_tokens.
            Use slicing operations to manage token usage.
            Max tokens set to 30000 to match LLM context limit.
            
            FIX: Keep system prompt (index 0-3) + recent messages only
            """
            total_tokens = sum(len(str(message)) for message in messages)
            if total_tokens <= max_tokens:
                return messages  # 如果总Token数不超过限制，返回原始消息列表

            # Keep first 4 messages (system prompt) + progressively remove old messages
            new_messages = messages[:]
            while sum(len(str(message)) for message in new_messages) > max_tokens and len(new_messages) > 4:
                # Remove 5th message (oldest conversation, not system prompt)
                if len(new_messages) > 4:
                    new_messages.pop(4)
                else:
                    break

            return new_messages
        
        # 传入内部指令，传出所有正确执行的历史指令
        def extract_cmds(inner_commands):
            """
            Extract SUCCESSFUL commands only - for Dockerfile generation
            """
            res_cmd = list()
            
            for inner_command in inner_commands:
                command = inner_command['command']
                dir = inner_command['dir'] if 'dir' in inner_command else '/'
                returncode = inner_command['returncode']
                action_name = command.split(' ')[0].strip()
                
                # Skip failed commands
                if str(returncode).strip() != '0':
                    continue
                
                # Skip analysis tools
                if command == 'python /home/tools/runtest.py' or command == 'python /home/tools/generate_diff.py' or command == '$pwd$':
                    continue
                
                # Skip clear_configuration (resets history)
                if action_name == 'clear_configuration':
                    res_cmd = list()
                    continue
                
                # Format command
                formatted_cmd = f'cd {dir} && {command}' if dir != '/' else command
                
                # Skip safe commands from main history
                if action_name in safe_cmd and '>' not in command:
                    continue
                
                # Add to main history
                res_cmd.append(formatted_cmd)
            
            return res_cmd
        
        def get_recent_history(inner_commands, max_recent=15):
            """
            Get recent command history (both success and failure) for LLM context
            Shows last N commands with their results
            
            v3.5: Commands are now split at execution time, so each command 
                  in inner_commands is already individual (no need to split &&)
            """
            recent = []
            all_cmds_for_loop_detection = []  # Track all for loop detection
            
            # Get last max_recent commands
            commands_to_show = inner_commands[-max_recent:] if len(inner_commands) > max_recent else inner_commands
            
            for inner_command in commands_to_show:
                command = inner_command['command']
                dir = inner_command['dir'] if 'dir' in inner_command else '/'
                returncode = inner_command['returncode']
                action_name = command.split(' ')[0].strip()
                
                # Skip analysis tools
                if command == 'python /home/tools/runtest.py' or command == 'python /home/tools/generate_diff.py' or command == '$pwd$':
                    continue
                
                # Skip clear_configuration
                if action_name == 'clear_configuration':
                    recent = []  # Clear history on reset
                    all_cmds_for_loop_detection = []
                    recent.append("✨ Container reset to initial state")
                    continue
                
                # Skip safe read-only commands (ls, cat, etc)
                if action_name in safe_cmd and '>' not in command:
                    continue
                
                # v3.5: Commands are already split - just show the command itself
                # Don't reconstruct chains using 'dir', as commands are already individual
                formatted_cmd = command
                
                # Track for loop detection
                all_cmds_for_loop_detection.append(formatted_cmd)
                
                # Show with status (now each command is already individual)
                # returncode can be: 0 (success), non-zero int (failure), or 'unknown' (special commands)
                if returncode == 0 or str(returncode).strip() == '0' or returncode == 'unknown':
                    recent.append(f"✅ {formatted_cmd}")
                else:
                    recent.append(f"❌ {formatted_cmd}")
            
            # Detect command repetition
            if len(all_cmds_for_loop_detection) >= 2:
                if all_cmds_for_loop_detection[-1] == all_cmds_for_loop_detection[-2]:
                    recent.append("")
                    recent.append("⚠️ WARNING: You just repeated the same command!")
            
            # Detect A-B-A loop
            if len(all_cmds_for_loop_detection) >= 3:
                if all_cmds_for_loop_detection[-1] == all_cmds_for_loop_detection[-3]:
                    recent.append("")
                    recent.append("="*60)
                    recent.append("🚨 CRITICAL: INFINITE LOOP DETECTED!")
                    recent.append("="*60)
                    recent.append("You are alternating between two commands that both fail!")
                    recent.append("🛑 This approach is NOT working!")
                    recent.append("📖 REQUIRED: Check INSTALL/README documentation")
                    recent.append("="*60)
            
            return recent

        finish = False  # Track if runtest passed
        while(turn < self.max_turn):
            turn += 1
            GPT_start_time = time.time()
            
            # v4.0: 10-turn reminder moved to system_res (line 704-721) for unified display
            
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
            elif len(commands) != 0: #按顺序执행工具
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
                    # Note: returncode intentionally not shown to AI to avoid over-focusing on it
                    # AI should read error messages instead
                    end_time = time.time()
                    elasped_time = end_time - start_time
                    self.outer_commands[-1]["time"] = elasped_time
                    self.outer_commands[-1]["returncode"] = return_code  # Store actual return code (not shown to LLM)
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
            
            # Get recent command history (success + failure) for LLM
            # max_recent=50 to ensure ~15 meaningful commands are shown after filtering
            recent_history = get_recent_history(self.sandbox.commands, max_recent=50)
            
            if len(recent_history) > 0:
                appendix = '\n' + '='*60 + '\n'
                appendix += f'📋 RECENT COMMAND HISTORY ({len(recent_history)} commands)\n'
                appendix += '   ✅ = success, ❌ = failed\n'
                appendix += '='*60 + '\n'
                appendix += '\n'.join(recent_history)
                appendix += '\n' + '='*60
                
                # v4.0: Every 10 turns, add documentation check reminder
                if turn % 10 == 0 and turn > 0:
                    appendix += '\n\n' + '🔔'*30 + '\n'
                    appendix += f'⚠️  CHECKPOINT (Turn {turn}) - Search docs for error keywords!\n'
                    appendix += '🔔'*30 + '\n'
                    appendix += '📖 Extract error keywords → grep them in docs (with context):\n'
                    appendix += '\n'
                    appendix += '  Example 1: Error mentions "bison" or "flex"\n'
                    appendix += '  → grep -iC 20 "bison" /repo/INSTALL /repo/README* 2>/dev/null || echo "Not found in docs"\n'
                    appendix += '\n'
                    appendix += '  Example 2: Missing "winscard.h" or library\n'
                    appendix += '  → grep -iC 20 "winscard" /repo/INSTALL /repo/README* 2>/dev/null || echo "Not found in docs"\n'
                    appendix += '🔔'*30 + '\n'
                
                appendix += '\n\nPlease refer to the execution history above, reflect on what worked and what failed, and decide the subsequent actions. Remember, your ultimate goal is to pass the verification by executing `python /home/tools/runtest.py`.'
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
            
            # DEBUG: Save the exact message sent to LLM
            with open(f'{self.root_dir}/output/{self.full_name}/llm_observation.txt', 'w') as debug_f:
                debug_f.write("="*80 + "\n")
                debug_f.write(f"TURN {turn}: MESSAGE TO LLM\n")
                debug_f.write("="*80 + "\n")
                debug_f.write(system_res)
                debug_f.write("\n" + "="*80 + "\n")
            
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
        
        # Configuration phase complete
        print()
        print("="*70)
        if finish:
            print("✅ CONFIGURATION COMPLETE: runtest passed!")
            print(f"🎯 Project: {self.full_name}")
            print(f"⏱️  Total time: {time.time() - start_time0:.1f}s")
            print(f"📊 Total turns: {turn}")
            print(f"💰 Total tokens: {cost_tokens}")
        else:
            print("❌ CONFIGURATION INCOMPLETE: Max turns reached")
            print(f"🎯 Project: {self.full_name}")
            print(f"⏱️  Total time: {time.time() - start_time0:.1f}s")
            print(f"📊 Total turns: {turn}/{self.max_turn}")
            print(f"💰 Total tokens: {cost_tokens}")
        print("="*70)
        print()
        
        append_trajectory(trajectory, self.messages, 'configuration')
        end_time0 = time.time()
        cost_time = end_time0 - start_time0
        trajectory.append({'agent': "configuration", 'cost_time': cost_time, 'cost_tokens': cost_tokens}) 
        self.sandbox_session.close()
        return trajectory, self.outer_commands
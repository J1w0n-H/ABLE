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
import sys
import subprocess
import json
import re
from utils.llm import get_llm_response
from utils.agent_util import extract_commands, extract_diffs, append_trajectory, save_diff_description
from utils.tools_config import Tools

class Agent:
    def __init__(self, sandbox, image_name, full_name, root_dir, max_turn=70):
        self.model = "gpt-4o-2024-05-13"
        self.root_dir = root_dir
        self.max_turn = max_turn
        self.sandbox = sandbox
        self.sandbox_session = self.sandbox.get_session()
        self.full_name = full_name
        
        # C-specific tools only
        self.tool_lib = [
            Tools.run_make,
            Tools.run_cmake, 
            Tools.run_gcc,
            Tools.apt_install,
        ]
        
        # C-specific prompt
        self.init_prompt = f"""\
You are an expert C build engineer. Your ONLY job is to build a C project in /repo directory.

CRITICAL RULES:
1. You MUST use bash commands wrapped in ```bash ``` blocks
2. First, check what files exist: ls /repo
3. Then execute ONE build command based on what you find
4. Do NOT explain - just execute commands

BUILD COMMANDS (use these EXACTLY as shown):
```bash
ls /repo
```

Then if you see:
- Makefile → use: ```bash
run_make
```
- CMakeLists.txt → use: ```bash
run_cmake
```
- Only .c files → use: ```bash
run_gcc
```

EXAMPLE SESSION:
Turn 1: ```bash
ls /repo
```
Turn 2: ```bash
run_make
```

Start now by checking the directory!
"""

    def run(self, work_dir, trajectory):
        """Run the configuration agent"""
        messages = [{"role": "system", "content": self.init_prompt}]
        outer_commands = []
        
        print(f"\n{'='*60}")
        print(f"Starting Configuration Agent (max {self.max_turn} turns)")
        print(f"{'='*60}\n")
        
        for turn in range(self.max_turn):
            print(f"\n--- Turn {turn + 1}/{self.max_turn} ---")
            
            # Get LLM response
            print("Calling LLM...")
            response, usage = get_llm_response(
                model=self.model,
                messages=messages,
                temperature=0.0,
                n=1,
                max_tokens=1024
            )
            
            if response is None:
                print("❌ LLM response failed - stopping agent")
                print("Please check:")
                print("  1. OPENAI_API_KEY environment variable is set")
                print("  2. API key has sufficient credits")
                print("  3. Network connectivity")
                break
            
            print(f"✓ LLM responded ({len(response)} chars)")
            print(f"\n{'='*60}")
            print("LLM Response:")
            print(response)
            print(f"{'='*60}\n")
            
            # Append assistant response
            messages.append({"role": "assistant", "content": response})
            
            # Extract commands from response
            commands = extract_commands(response)
            
            if not commands:
                # No commands found, check if we're done
                if "Congratulations, you have successfully built the C project!" in response:
                    print("C project built successfully!")
                    break
                else:
                    # Continue with next turn
                    messages.append({"role": "user", "content": "Please continue building the C project."})
                    continue
            
            # Execute commands
            command_results = []
            for cmd in commands:
                print(f"\n{'>'*60}")
                print(f"Executing: {cmd}")
                print(f"{'>'*60}")
                outer_commands.append(cmd)
                
                success, output = self.sandbox_session.execute_simple(cmd)
                
                print(f"\n{'<'*60}")
                print(f"Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
                print(f"{'<'*60}")
                print(output)
                print(f"{'<'*60}\n")
                
                if success:
                    command_results.append(f"Command '{cmd}' executed successfully:\n{output}")
                else:
                    command_results.append(f"Command '{cmd}' failed:\n{output}")
            
            # Append results to messages
            if command_results:
                result_text = "\n\n".join(command_results)
                messages.append({"role": "user", "content": f"Command execution results:\n{result_text}"})
            
            # Check for success
            if any("successfully built the C project" in result.lower() for result in command_results):
                print("C project build completed successfully!")
                break
        
        # Save trajectory
        append_trajectory(trajectory, messages, "Configuration")
        
        return messages, outer_commands

class Configuration(Agent):
    """C-specific configuration agent"""
    pass

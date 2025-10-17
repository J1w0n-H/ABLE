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
import os
import re
import json

# Safe commands that don't modify system state
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

TIME_OUT_LABEL = ' seconds. Partial output:'
DIFF_FENCE = ["```diff", "```"]
BASH_FENCE = ["```bash", "```"]
HEAD = "<<<<<<< SEARCH"
DIVIDER = "======="
UPDATED = ">>>>>>> REPLACE"

INIT_PROMPT = f"""
IN GOOD FORMAT: 
All your answer must contain Thought and Action. 
Calling CLI tools Action using bash block like {BASH_FENCE[0]}  {BASH_FENCE[1]}. 
"""

EDIT_PROMPT = f"""
IN EDIT FORMAT:
If you want to edit a file, use diff block like {DIFF_FENCE[0]}
/path/to/file
{HEAD}
    exact copy of old line(s) you would like to change
{DIVIDER}
    new line(s) to replace
{UPDATED}
{DIFF_FENCE[1]}
"""

def extract_commands(text):
    """Extract bash commands from text"""
    commands = []
    # Find all ```bash ... ``` blocks
    pattern = r'```bash\s*\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    for match in matches:
        lines = match.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                commands.append(line)
    
    return commands

def extract_diffs(text):
    """Extract diff blocks from text"""
    pattern = r'```diff\s*\n(.*?)\n```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches[0] if matches else ""

def safe_cmd(command):
    """Check if command is safe (read-only)"""
    cmd_name = command.split()[0] if command else ""
    return cmd_name in safe_cmd and '>' not in command

def append_trajectory(trajectory, messages, agent_name):
    """Append messages to trajectory"""
    trajectory.append({
        'agent': agent_name,
        'messages': messages
    })

def save_diff_description(diffs):
    """Save diff to temporary file"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.diff') as f:
        f.write(diffs)
        return f.name

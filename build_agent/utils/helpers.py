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

SAFE_COMMANDS = [
    "ls", "cat", "echo", "pwd", "whoami", "who", "date", "cal", "df", "du",
    "free", "uname", "w", "ps", "pgrep", "top", "htop", "vmstat", "iostat",
    "dmesg", "tail", "head", "more", "less", "grep", "find", "locate", "whereis", "which",
    "file", "stat", "cmp", "diff", "md5sum", "sha256sum", "gzip", "gunzip", "bzip2", "bunzip2",
    "xz", "unxz", "sort", "uniq", "wc", "tr", "cut", "paste", "tee", "awk", "sed", "env", "printenv",
    "hostname", "ping", "traceroute", "ssh", "journalctl","lsblk", "blkid", "uptime",
    "lscpu", "lsusb", "lspci", "lsmod", "dmidecode", "ip", "ifconfig", "netstat", "ss", "route", "nmap",
    "strace", "ltrace", "time", "nice", "renice", "killall", "printf"
]

def truncate_msg(result_message, command, truncate=1000, bar_truncate=20, returncode=0):
    """
    Truncate command output intelligently.
    
    v3.9 Simple rules:
    - FAILURE (returncode != 0):
      - ≤50 lines: Show full
      - >50 lines: Save to file + show first/last 25 lines each (50 total)
    
    - SUCCESS (returncode == 0):
      - ≤50 lines: Show full
      - >50 lines: Show first 25 + last 25 lines (50 total)
    """
    lines = result_message.splitlines()
    # Keep all lines including empty ones for context
    line_count = len(lines)
    
    # ========================================
    # FAILURE: Show full or save to file
    # ========================================
    if returncode != 0:
        if line_count <= 50:
            # Short error: show full
            return result_message
        else:
            # Long error: save to file + show summary
            # Use /repo/ instead of /tmp/ so Docker container can access it
            output_file = '/repo/error_output.txt'
            try:
                with open(output_file, 'w') as f:
                    f.write(result_message)
                file_saved = True
            except:
                file_saved = False
                # Fallback: try /tmp/ (host only)
                try:
                    output_file = '/tmp/last_error_output.txt'
                    with open(output_file, 'w') as f:
                        f.write(result_message)
                    file_saved = True
                except:
                    file_saved = False
            
            summary = f"⚠️  Error output too long ({line_count} lines)\n"
            if file_saved:
                summary += f"📁 Full output saved to: {output_file}\n\n"
                summary += "💡 Read the file to see all errors:\n"
                summary += f"   - cat {output_file}\n"
                summary += f"   - tail -100 {output_file}\n"
                summary += f"   - grep -i 'error' {output_file}\n\n"
            
            summary += "━━━ First 25 lines ━━━\n"
            summary += '\n'.join(lines[:25]) + "\n\n"
            summary += f"... ({line_count - 50} lines omitted) ...\n\n"
            summary += "━━━ Last 25 lines ━━━\n"
            summary += '\n'.join(lines[-25:])
            
            return summary
    
    # ========================================
    # SUCCESS: Show full or truncate
    # ========================================
    else:
        if line_count <= 50:
            # Short success: show full
            return result_message
        else:
            # Long success: show first 25 + last 25 (50 total)
            truncated = '\n'.join(lines[:25])
            truncated += f"\n\n... ({line_count - 50} lines omitted) ...\n\n"
            truncated += '\n'.join(lines[-25:])
            return truncated

def get_waitinglist_error_msg():
    """Get error message for waitinglist command"""
    return '''waitinglist command usage error, the following command formats are leagal:
1. `waitinglist add -p package_name1 -t apt`
Explanation: Add package_name1 into waiting list(using apt-get), no version means install the latest available version by default.
2. `waitinglist addfile /path/to/file`
Explanation: Add all the items in the /path/to/file into waiting list. Note that you must make sure each line contains a valid package name.
3. `waitinglist clear`
Explanation: Clear all the items in the waiting list.'''

def get_conflict_error_msg():
    """Get error message for conflictlist command"""
    return '''conflictlist command usage error, the following command formats are legal:
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


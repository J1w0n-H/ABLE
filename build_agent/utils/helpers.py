#!/usr/bin/env python3
"""
Common helper functions and constants
Extracted to avoid circular imports between sandbox.py and command_handlers.py
"""

# Safe commands that don't modify system state
SAFE_COMMANDS = [
    "cd", "ls", "cat", "echo", "pwd", "whoami", "who", "date", "cal", "df", "du",
    "free", "uname", "uptime", "w", "ps", "pgrep", "top", "htop", "vmstat", "iostat",
    "dmesg", "tail", "head", "more", "less", "grep", "find", "locate", "whereis", "which",
    "file", "stat", "cmp", "diff", "md5sum", "sha256sum", "gzip", "gunzip", "bzip2", "bunzip2",
    "xz", "unxz", "sort", "uniq", "wc", "tr", "cut", "paste", "tee", "awk", "sed", "env", "printenv",
    "hostname", "ping", "traceroute", "ssh", "journalctl","lsblk", "blkid", "uptime",
    "lscpu", "lsusb", "lspci", "lsmod", "dmidecode", "ip", "ifconfig", "netstat", "ss", "route", "nmap",
    "strace", "ltrace", "time", "nice", "renice", "killall", "printf"
]

def truncate_msg(result_message, command, truncate=1000, bar_truncate=20, returncode=0):
    """
    Truncate command output intelligently:
    - <= 20 lines: Show full output (regardless of returncode)
    - > 20 lines && returncode=0: Show first 10 + last 10 lines
    - > 20 lines && returncode!=0: Show full output (errors need full context)
    """
    lines = result_message.splitlines()
    lines = [x for x in lines if len(x.strip()) > 0]
    line_count = len(lines)
    
    # 1. 20줄 이하 -> 전체 출력 (리턴코드 무관)
    if line_count <= 20:
        return result_message
    
    # 2. 20줄 이상
    if returncode == 0:
        # 성공이면 앞뒤 10줄씩만 (토큰 절약)
        truncated_output = '\n'.join(lines[:10] + [f'... ({line_count - 20} lines omitted) ...'] + lines[-10:])
        return truncated_output
    else:
        # 실패면 전체 출력 (디버깅 필요)
        return result_message

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


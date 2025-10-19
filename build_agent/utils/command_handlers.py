#!/usr/bin/env python3
"""
Command Handler Pattern for Sandbox Execution

Separates command execution logic into individual handlers for better:
- Testability
- Maintainability  
- Extensibility
- Readability
"""

from abc import ABC, abstractmethod
from outputcollector import OutputCollector
from download import download
from parser.parse_command import (
    match_download, match_runtest, match_conflict_solve,
    match_waitinglist_add, match_waitinglist_addfile,
    match_conflictlist_clear, match_waitinglist_clear,
    match_waitinglist_show, match_conflictlist_show
)
from helpers import truncate_msg, SAFE_COMMANDS, get_waitinglist_error_msg, get_conflict_error_msg
import time
import pexpect

# ========================================
# Base Handler
# ========================================

class CommandHandler(ABC):
    """Base class for command handlers"""
    
    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Check if this handler can process the command"""
        pass
    
    @abstractmethod
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        """Execute the command and return (result_message, return_code)"""
        pass

# ========================================
# Special Command Handlers
# ========================================

class PwdCommandHandler(CommandHandler):
    """Handle $pwd$ special command"""
    
    def can_handle(self, command: str) -> bool:
        return command.lower().strip() == '$pwd$'
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        session.sandbox.shell.sendline('pwd')
        session.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
        output = session.sandbox.shell.before.decode('utf-8').strip()
        output = output.replace('\x1b[?2004l\r', '')
        
        output_lines = output.split('\r\n')
        if len(output_lines) > 1:
            last_line = output_lines[-1]
            output_lines = output_lines[1:-1]
            id = last_line.find('\x1b[')
            if id != -1 and len(last_line[:id].strip()) > 0:
                output_lines.append(last_line[:id].strip())
        
        return output_lines[0] if output_lines else '/', 0

class PipListCommandHandler(CommandHandler):
    """Handle $pip list --format json$ special command"""
    
    def can_handle(self, command: str) -> bool:
        return command.lower().strip() == '$pip list --format json$'
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        session.sandbox.shell.sendline('pip list --format json')
        session.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
        output = session.sandbox.shell.before.decode('utf-8').strip()
        output = output.replace('\x1b[?2004l\r', '')
        
        output_lines = output.split('\r\n')
        if len(output_lines) > 1:
            last_line = output_lines[-1]
            output_lines = output_lines[1:-1]
            id = last_line.find('\x1b[')
            if id != -1 and len(last_line[:id].strip()) > 0:
                output_lines.append(last_line[:id].strip())
        
        return output_lines[0] if output_lines else '[]', 0

# ========================================
# Tool Command Handlers
# ========================================

class DownloadCommandHandler(CommandHandler):
    """Handle download command"""
    
    def can_handle(self, command: str) -> bool:
        return match_download(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        with OutputCollector() as collector:
            download(session, waiting_list, conflict_list)
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, 'download'), 'unknown'

class RuntestCommandHandler(CommandHandler):
    """Handle runtest command"""
    
    def can_handle(self, command: str) -> bool:
        return match_runtest(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        # Convert to actual tool path
        return 'python /home/tools/runtest.py', None

class WaitingListAddHandler(CommandHandler):
    """Handle waitinglist add command"""
    
    def can_handle(self, command: str) -> bool:
        return match_waitinglist_add(command) != -1
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        parsed = match_waitinglist_add(command)
        package_name = parsed['package_name']
        version_constraints = parsed['version_constraints']
        tool = parsed['tool']
        
        with OutputCollector() as collector:
            waiting_list.add(package_name, version_constraints, tool, conflict_list)
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class WaitingListAddFileHandler(CommandHandler):
    """Handle waitinglist addfile command"""
    
    def can_handle(self, command: str) -> bool:
        return match_waitinglist_addfile(command) != -1
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        import os
        import subprocess
        
        parsed = match_waitinglist_addfile(command)
        file_path = parsed['file_path']
        
        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        project_directory = os.path.dirname(current_directory)
        
        result = subprocess.run(
            f'docker cp {session.sandbox.container.name}:{file_path} {project_directory}/utils/repo/{session.sandbox.full_name}/repo',
            shell=True, capture_output=True
        )
        
        if result.returncode != 0:
            msg = f'\nRunning `{command}`...\n'
            msg += f'The file {file_path} does not exist. Please ensure you have entered the correct absolute path!'
            return msg, 1
        
        subprocess.run(
            f'sudo chown huruida:huruida {project_directory}/repo/{session.sandbox.full_name}/repo/{file_path.split("/")[-1]}',
            shell=True, capture_output=True
        )
        
        with OutputCollector() as collector:
            waiting_list.addfile(
                f'{project_directory}/utils/repo/{session.sandbox.full_name}/repo/{file_path.split("/")[-1]}',
                conflict_list
            )
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class WaitingListClearHandler(CommandHandler):
    """Handle waitinglist clear command"""
    
    def can_handle(self, command: str) -> bool:
        return match_waitinglist_clear(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        with OutputCollector() as collector:
            waiting_list.clear()
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class WaitingListShowHandler(CommandHandler):
    """Handle waitinglist show command"""
    
    def can_handle(self, command: str) -> bool:
        return match_waitinglist_show(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        with OutputCollector() as collector:
            waiting_list.get_message()
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class ConflictSolveHandler(CommandHandler):
    """Handle conflictlist solve command"""
    
    def can_handle(self, command: str) -> bool:
        return match_conflict_solve(command) != -1
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        parsed = match_conflict_solve(command)
        version_constraint = parsed['version_constraint']
        unchanged = parsed['unchanged']
        
        with OutputCollector() as collector:
            conflict_list.solve(waiting_list, version_constraint, unchanged)
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class ConflictClearHandler(CommandHandler):
    """Handle conflictlist clear command"""
    
    def can_handle(self, command: str) -> bool:
        return match_conflictlist_clear(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        with OutputCollector() as collector:
            conflict_list.clear()
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

class ConflictShowHandler(CommandHandler):
    """Handle conflictlist show command"""
    
    def can_handle(self, command: str) -> bool:
        return match_conflictlist_show(command)
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        with OutputCollector() as collector:
            conflict_list.get_message(waiting_list)
        result_message = f'Running `{command}`...\n' + collector.get_output() + '\n'
        return truncate_msg(result_message, command), 'unknown'

# ========================================
# Validation Handlers
# ========================================

class InteractiveShellBlockHandler(CommandHandler):
    """Block interactive shell commands"""
    
    def can_handle(self, command: str) -> bool:
        return 'hatch shell' == command.lower().strip()
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        return 'You are not allowed to use commands like `hatch shell` that would open a new shell!!!', -1

class PytestBlockHandler(CommandHandler):
    """Block pytest in C/C++ projects"""
    
    def can_handle(self, command: str) -> bool:
        return 'pytest' in command.lower() and 'pip' not in command.lower()
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        msg = 'This is a C/C++ project. Use `runtest` instead (which runs ctest or make test for C/C++ projects).'
        return msg, 1

class TestFileDeleteBlockHandler(CommandHandler):
    """Block deletion of test files"""
    
    def can_handle(self, command: str) -> bool:
        if command.split(' ')[0] != 'rm':
            return False
        filename = command.split('/')[-1]
        return filename.startswith('test_') or filename.endswith('_test.py')
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        return 'Please do not directly delete the testing file to pass the test!', 1

class TestFileMoveBlockHandler(CommandHandler):
    """Block moving of test files"""
    
    def can_handle(self, command: str) -> bool:
        if command.split(' ')[0] != 'mv':
            return False
        filename = command.split('/')[-1]
        return filename.startswith('test_') or filename.endswith('_test.py')
    
    def execute(self, command: str, session, waiting_list, conflict_list) -> tuple:
        return 'Please do not directly move the testing file to pass the test!', 1

# ========================================
# Command Executor (Main Router)
# ========================================

class CommandExecutor:
    """
    Main command router using Command Pattern.
    Routes commands to appropriate handlers.
    """
    
    def __init__(self):
        # Order matters! Check specific patterns before generic ones
        self.handlers = [
            # Special commands (highest priority)
            InteractiveShellBlockHandler(),
            PwdCommandHandler(),
            PipListCommandHandler(),
            
            # Validation handlers
            PytestBlockHandler(),
            TestFileDeleteBlockHandler(),
            TestFileMoveBlockHandler(),
            
            # Tool commands
            DownloadCommandHandler(),
            RuntestCommandHandler(),
            WaitingListAddHandler(),
            WaitingListAddFileHandler(),
            WaitingListClearHandler(),
            WaitingListShowHandler(),
            ConflictSolveHandler(),
            ConflictClearHandler(),
            ConflictShowHandler(),
        ]
    
    def find_handler(self, command: str):
        """Find appropriate handler for command"""
        for handler in self.handlers:
            if handler.can_handle(command):
                return handler
        return None
    
    def execute(self, command: str, session, waiting_list, conflict_list, timeout=600):
        """
        Execute command using appropriate handler.
        Falls back to bash execution if no handler found.
        """
        # Try to find a handler
        handler = self.find_handler(command)
        
        if handler:
            # Special handling for runtest (needs conversion)
            if isinstance(handler, RuntestCommandHandler):
                converted_command, _ = handler.execute(command, session, waiting_list, conflict_list)
                # Continue to bash execution with converted command
                return self._execute_bash(converted_command, session, waiting_list, conflict_list, timeout)
            else:
                # Execute with handler
                return handler.execute(command, session, waiting_list, conflict_list)
        else:
            # No handler found - execute as bash command
            return self._execute_bash(command, session, waiting_list, conflict_list, timeout)
    
    def _execute_bash(self, command: str, session, waiting_list, conflict_list, timeout=600):
        """
        Execute bash command in container shell.
        This is the fallback for generic commands.
        """
        # Convert some special commands
        if command == 'generate_diff':
            command = 'python /home/tools/generate_diff.py'
        
        # Determine if command changes state
        action_name = command.split()[0].strip() if command else ''
        is_safe = (action_name in SAFE_COMMANDS and '>' not in command)
        
        # Commit container before dangerous commands
        if not is_safe:
            session.sandbox.commit_container()
        
        # Get current directory
        dir, _ = session.execute('$pwd$', waiting_list, conflict_list)
        
        # Record command
        start_time = time.time()
        session.sandbox.commands.append({
            "command": command,
            "returncode": -2,
            "time": -1,
            "dir": dir
        })
        
        # Execute command
        if command.endswith('&'):
            session.sandbox.shell.sendline(command)
        else:
            session.sandbox.shell.sendline(command + " && sleep 0.5")
        
        session.sandbox.commands[-1]["returncode"] = -1
        
        # Wait for completion
        session.sandbox.shell.expect([r'root@.*:.*# '], timeout=timeout*2)
        end_time = time.time()
        elapsed_time = end_time - start_time
        session.sandbox.commands[-1]["time"] = elapsed_time
        
        # Parse output
        output = session.sandbox.shell.before.decode('utf-8').strip()
        output = output.replace('\x1b[?2004l\r', '')
        output_lines = output.split('\r\n')
        
        if len(output_lines) > 1:
            last_line = output_lines[-1]
            output_lines = output_lines[1:-1]
            id = last_line.find('\x1b[')
            if id != -1 and len(last_line[:id].strip()) > 0:
                output_lines.append(last_line[:id].strip())
        
        # Get return code
        try:
            return_code = session.get_returncode()
        except:
            return_code = 123
        
        try:
            session.sandbox.commands[-1]["returncode"] = return_code
        except:
            session.sandbox.commands[-1]["returncode"] = 111
            session.sandbox.commands[-1]["error_msg"] = return_code
        
        # Handle errors
        if return_code != 0 and not (command == 'python /home/tools/runtest.py' and return_code == 5):
            # Show error message for specific command types
            if command.strip().lower().startswith('conflict'):
                msg = get_conflict_error_msg()
                result_message = f'Running `{command}`...\n' + msg + '\n'
                return result_message, return_code
            elif command.strip().lower().startswith('waiting'):
                msg = get_waitinglist_error_msg()
                result_message = f'Running `{command}`...\n' + msg + '\n'
                return result_message, return_code
            
            # Rollback if command failed and not safe
            if not is_safe:
                session.sandbox.switch_to_pre_image()
                output_lines.append('The command execution failed, so I have reverted it back to the previous state.')
            else:
                output_lines.append('The command execution failed, please carefully check the output!')
        
        # Format result
        result_message = '\n'.join(output_lines)
        
        # Don't add prefix for special commands
        if 'Congratulations, you have successfully configured the environment!' in result_message or \
           command == 'python /home/tools/generate_diff.py' or \
           command in ['pipdeptree --json-tree', 'pipdeptree']:
            return result_message, return_code
        else:
            result_message = f'Running `{command}`...\n' + result_message + '\n'
            return truncate_msg(result_message, command, returncode=return_code), return_code

# ========================================
# Usage Example
# ========================================

if __name__ == '__main__':
    """
    Example usage:
    
    executor = CommandExecutor()
    result, code = executor.execute(command, session, waiting_list, conflict_list)
    """
    pass


#!/usr/bin/env python3
"""
Simple test for command handlers
"""

import sys
sys.path.insert(0, '/root/Git/ARVO2.0/build_agent/utils')

from command_handlers import (
    CommandExecutor,
    PwdCommandHandler,
    DownloadCommandHandler,
    WaitingListAddHandler,
    InteractiveShellBlockHandler
)

def test_handler_matching():
    """Test if handlers can match commands correctly"""
    print("=" * 60)
    print("Command Handler 매칭 테스트")
    print("=" * 60)
    
    executor = CommandExecutor()
    
    test_cases = [
        ('$pwd$', 'PwdCommandHandler'),
        ('download', 'DownloadCommandHandler'),
        ('waitinglist add -p libssl-dev -t apt', 'WaitingListAddHandler'),
        ('hatch shell', 'InteractiveShellBlockHandler'),
        ('make -j4', None),  # No special handler (bash execution)
        ('ls /repo', None),
    ]
    
    for command, expected_handler in test_cases:
        handler = executor.find_handler(command)
        handler_name = handler.__class__.__name__ if handler else None
        
        if expected_handler:
            if handler_name == expected_handler:
                print(f"✅ '{command[:30]}' → {handler_name}")
            else:
                print(f"❌ '{command[:30]}' → Expected {expected_handler}, got {handler_name}")
        else:
            if handler is None:
                print(f"✅ '{command[:30]}' → Bash execution (no handler)")
            else:
                print(f"⚠️  '{command[:30]}' → {handler_name} (expected bash)")
    
    print("")
    print(f"총 핸들러 개수: {len(executor.handlers)}")
    print("")

if __name__ == '__main__':
    test_handler_matching()
    print("✅ 모든 테스트 완료!")


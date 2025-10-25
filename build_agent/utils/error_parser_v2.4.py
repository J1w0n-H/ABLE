# Copyright (2025) Bytedance Ltd. and/or its affiliates 
#
# Licensed under the Apache License, Version 2.0 (the "License"); 
# you may not use this file except in compliance with the License. 
# You may obtain a copy of the License at 
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software 
# distributed under the License is distributed on an "AS IS" BASIS, 
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. 
# See the License for the specific language governing permissions and 
# limitations under the License. 

"""
error_parser v2.4: Philosophy Improvement

CORE PRINCIPLES:
1. Only suggest when 100% sure
2. Trust the LLM - it's smart enough
3. Show full error, avoid generic suggestions
4. Less is more - minimal parser, maximum LLM autonomy
"""

import re

def extract_critical_errors(output, returncode):
    """
    Extract critical error messages from command output.
    Returns a formatted error summary or empty string if no errors found.
    
    v2.4 CHANGES:
    - Expanded error context (15 → 30 lines)
    - More conservative suggestion filtering
    """
    if returncode == 0:
        return ""
    
    lines = output.split('\n')
    error_lines = []
    
    # Error patterns to match
    error_patterns = [
        r'\*\*\* \[.+?\] Error \d+',  # make errors: *** [target] Error 127
        r'error:',                      # compiler errors
        r'fatal error:',                # fatal errors
        r'undefined reference to',      # linker errors
        r'No such file or directory',  # missing files
        r'command not found',           # missing commands
        r'configure: error:',           # configure errors
        r'Error \d+',                   # generic errors with codes
    ]
    
    for line in lines:
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_lines.append(line.strip())
                break
    
    # Also look for specific warnings that are critical
    warning_patterns = [
        r'Makeinfo is missing',
        r'WARNING:.*required',
    ]
    
    for line in lines:
        for pattern in warning_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_lines.append(line.strip())
                break
    
    if not error_lines:
        return ""
    
    # Build error summary
    summary = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    summary += "🚨 CRITICAL ERRORS DETECTED:\n"
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # v2.4: Show MORE error lines (15 → 30) to give LLM better context
    unique_errors = []
    for error in reversed(error_lines):
        if error not in unique_errors:
            unique_errors.append(error)
        if len(unique_errors) >= 30:  # Increased from 15
            break
    
    for i, error in enumerate(reversed(unique_errors), 1):
        summary += f"{i}. {error}\n"
    
    # Add suggestions based on error patterns
    suggestions = analyze_errors(error_lines)
    if suggestions:
        summary += "\n💡 SUGGESTED FIXES (참고용 - 직접 분석하세요):\n"
        for suggestion in suggestions:
            summary += f"   • {suggestion}\n"
    else:
        # v2.4: If no specific suggestion, encourage LLM to analyze
        summary += "\n🤔 분석 권장: 에러 메시지를 직접 분석하여 해결 방법을 찾으세요.\n"
    
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return summary


def analyze_errors(error_lines):
    """
    Analyze error lines and provide suggestions.
    
    v2.4 PHILOSOPHY:
    - Only suggest when we're 100% certain
    - Prefer letting LLM analyze the error
    - Avoid generic suggestions like "check dependencies"
    - Map specific errors to specific solutions
    
    RETURNS:
    - Empty list if uncertain (let LLM decide)
    - Specific commands if certain
    """
    suggestions = set()
    error_text = '\n'.join(error_lines)
    
    # ═══════════════════════════════════════════════════════════════
    # Error 127 = command not found (SPECIFIC COMMANDS ONLY!)
    # ═══════════════════════════════════════════════════════════════
    if 'Error 127' in error_text:
        # Exact command-to-package mapping
        command_packages = {
            'makeinfo': 'texinfo',
            'aclocal': 'automake',
            'autoconf': 'autoconf',
            'autoheader': 'autoconf',
            'autom4te': 'autoconf',
            'libtoolize': 'libtool',
            'glibtoolize': 'libtool',
            '/usr/bin/file': 'file',
            'file': 'file',
            'pkg-config': 'pkg-config',
            'cmake': 'cmake',
            'yacc': 'bison',
            'bison': 'bison',
            'flex': 'flex',
            'lex': 'flex',
            'gperf': 'gperf',
            'nasm': 'nasm',
            'yasm': 'yasm',
        }
        
        found = False
        for cmd, pkg in command_packages.items():
            if cmd in error_text.lower():
                suggestions.add(f"apt-get install {pkg}")
                found = True
                break  # Only one suggestion per error
        
        # If no specific match, don't suggest anything
        # Let LLM analyze the "command not found" message
    
    # ═══════════════════════════════════════════════════════════════
    # Missing headers (SPECIFIC HEADERS ONLY!)
    # ═══════════════════════════════════════════════════════════════
    if 'fatal error:' in error_text and '.h:' in error_text:
        # Exact header-to-package mapping
        header_packages = {
            'zlib.h': 'zlib1g-dev',
            'openssl/ssl.h': 'libssl-dev',
            'ssl.h': 'libssl-dev',
            'Python.h': 'python3-dev',
            'curses.h': 'libncurses-dev',
            'ncurses.h': 'libncurses-dev',
            'readline/readline.h': 'libreadline-dev',
            'curl/curl.h': 'libcurl4-openssl-dev',
            'png.h': 'libpng-dev',
            'jpeglib.h': 'libjpeg-dev',
            'tiffio.h': 'libtiff-dev',
        }
        
        for header, pkg in header_packages.items():
            if header in error_text:
                suggestions.add(f"apt-get install {pkg}")
                break
    
    # ═══════════════════════════════════════════════════════════════
    # ❌ REMOVED: Generic "undefined reference" suggestions
    # Let LLM analyze linker errors by itself!
    # ═══════════════════════════════════════════════════════════════
    # The Float16 case was a SYMPTOM of over-eager parsing.
    # LLM should be able to see "undefined reference to __extendhfsf2"
    # and infer it's a Float16 issue, then try:
    # 1. CMake options to disable Float16
    # 2. Switch to GCC
    # 3. Install libgcc
    #
    # We DON'T need to pre-parse every possible linker error!
    
    # ═══════════════════════════════════════════════════════════════
    # Configure errors (ONLY if obvious solution exists)
    # ═══════════════════════════════════════════════════════════════
    if 'configure: error:' in error_text:
        # Only suggest if there's a clear library name mentioned
        if 'library' in error_text.lower() and 'not found' in error_text.lower():
            # Extract library name and suggest apt-cache search
            # But DON'T make assumptions about the package name
            pass  # Let LLM handle this
    
    return list(suggestions)


def should_suggest_single_thread(command, output):
    """
    Determine if we should suggest single-threaded build.
    
    v2.4: REMOVED - this is micromanagement.
    LLM can decide if parallel build is causing issues.
    """
    return False  # Trust LLM to decide


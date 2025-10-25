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
error_parser v2.4 (Improved): Tiered Suggestion System

CORE PRINCIPLES:
1. MANDATORY (⛔): Error 127, Missing Headers - always correct
2. RECOMMENDED (✅): Library dependencies - usually correct  
3. ADVISORY (💡): Complex errors - hints only
4. Show full context (30 lines) for LLM analysis
"""

import re

def extract_critical_errors(output, returncode):
    """
    Extract critical error messages from command output.
    Returns a formatted error summary or empty string if no errors found.
    
    v2.4 IMPROVEMENTS:
    - Tiered suggestion system (MANDATORY/RECOMMENDED/ADVISORY)
    - Better Error 127 detection (case-insensitive)
    - Expanded context (30 lines)
    """
    if returncode == 0:
        return ""
    
    lines = output.split('\n')
    error_lines = []
    
    # Error patterns to match
    error_patterns = [
        r'\*\*\* \[.+?\] Error \d+',  # make errors
        r'error:',                      # compiler errors
        r'fatal error:',                # fatal errors
        r'undefined reference to',      # linker errors
        r'No such file or directory',  # missing files
        r'command not found',           # missing commands
        r'configure: error:',           # configure errors
        r'Error \d+',                   # generic errors
    ]
    
    for line in lines:
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_lines.append(line.strip())
                break
    
    # Warning patterns (case-insensitive!)
    warning_patterns = [
        r'makeinfo is missing',  # Case-insensitive!
        r'WARNING:.*required',
    ]
    
    for line in lines:
        for pattern in warning_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                error_lines.append(line.strip())
                break
    
    if not error_lines:
        return ""
    
    # Analyze and classify suggestions FIRST
    suggestions = analyze_errors(error_lines)
    error_text = '\n'.join(error_lines)
    
    mandatory = []
    recommended = []
    advisory = []
    
    if suggestions:
        for suggestion in suggestions:
            tier = classify_suggestion(suggestion, error_text)
            if tier == 1:
                mandatory.append(suggestion)
            elif tier == 2:
                recommended.append(suggestion)
            else:
                advisory.append(suggestion)
    
    # Build error summary - MANDATORY FIRST!
    summary = ""
    
    # 🆕 CRITICAL: Show MANDATORY at the VERY TOP!
    if mandatory:
        summary += "\n" + "="*70 + "\n"
        summary += "🔴🔴🔴 STOP! MANDATORY ACTION REQUIRED 🔴🔴🔴\n"
        summary += "="*70 + "\n"
        summary += "READ THIS FIRST - DO NOT SKIP!\n\n"
        for s in mandatory:
            summary += f"   ⛔ {s}\n"
        summary += "\nYou MUST execute these commands immediately!\n"
        summary += "Then retry your LAST command (the one that just failed).\n"
        summary += "="*70 + "\n\n"
    
    # Then show error details
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    summary += "🚨 CRITICAL ERRORS DETECTED:\n"
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Show 30 lines for better context
    unique_errors = []
    for error in reversed(error_lines):
        if error not in unique_errors:
            unique_errors.append(error)
        if len(unique_errors) >= 30:
            break
    
    for i, error in enumerate(reversed(unique_errors), 1):
        summary += f"{i}. {error}\n"
    
    # Show other tier suggestions
    if recommended:
        summary += "\n🟡 RECOMMENDED ACTIONS:\n"
        summary += "You should follow these (usually correct):\n"
        for s in recommended:
            summary += f"   ✅ {s}\n"
    
    if advisory:
        summary += "\n🟢 ADVISORY (Optional):\n"
        summary += "Consider these as hints:\n"
        for s in advisory:
            summary += f"   💡 {s}\n"
    
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return summary


def classify_suggestion(suggestion, error_text):
    """
    Classify suggestion into tier.
    
    Returns:
        1: MANDATORY (Error 127, missing headers) - must follow
        2: RECOMMENDED (libraries, configure) - should follow
        3: ADVISORY (complex issues) - may consider
    """
    # TIER 1: Command not found (Error 127)
    if 'Error 127' in error_text:
        # Build tool packages are mandatory
        build_tools = ['texinfo', 'autoconf', 'automake', 'libtool', 
                       'pkg-config', 'file', 'cmake', 'bison', 'flex']
        if any(tool in suggestion for tool in build_tools):
            return 1
    
    # TIER 1: Missing headers (fatal error)
    if 'fatal error:' in error_text and '.h' in error_text:
        return 1
    
    # TIER 2: Library dependencies
    lib_packages = ['libgmp', 'libmpfr', 'libmpc', 'libssl', 'zlib', 
                    'libcurl', 'libpng', 'libjpeg', 'python3-dev']
    if any(lib in suggestion for lib in lib_packages):
        return 2
    
    # TIER 2: Configure errors
    if 'configure: error:' in error_text:
        return 2
    
    # TIER 3: Everything else
    return 3


def analyze_errors(error_lines):
    """
    Analyze error lines and provide suggestions.
    
    v2.4: Simple and focused - only suggest what we're certain about.
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
        
        for cmd, pkg in command_packages.items():
            if cmd in error_text.lower():
                suggestions.add(f"apt-get install {pkg}")
                break
    
    # ═══════════════════════════════════════════════════════════════
    # Missing headers (SPECIFIC HEADERS ONLY!)
    # ═══════════════════════════════════════════════════════════════
    if 'fatal error:' in error_text:
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
    
    return list(suggestions)


def should_suggest_single_thread(command, output):
    """
    Determine if we should suggest single-threaded build.
    v2.4: Minimal - let LLM decide.
    """
    return False

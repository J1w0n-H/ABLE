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

import re

def extract_critical_errors(output, returncode):
    """
    Extract critical error messages from command output.
    Returns a formatted error summary or empty string if no errors found.
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
    
    # Show last 15 unique error lines (most recent are usually most relevant)
    unique_errors = []
    for error in reversed(error_lines):
        if error not in unique_errors:
            unique_errors.append(error)
        if len(unique_errors) >= 15:
            break
    
    for i, error in enumerate(reversed(unique_errors), 1):
        summary += f"{i}. {error}\n"
    
    # Add suggestions based on error patterns
    suggestions = analyze_errors(error_lines)
    if suggestions:
        summary += "\n💡 SUGGESTED FIXES:\n"
        for suggestion in suggestions:
            summary += f"   • {suggestion}\n"
    
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    return summary


def analyze_errors(error_lines):
    """
    Analyze error lines and provide suggestions.
    IMPROVED VERSION: Detects more common missing build tools.
    """
    suggestions = set()
    error_text = '\n'.join(error_lines)
    
    # ═══════════════════════════════════════════════════════════════
    # Error 127 = command not found (MOST CRITICAL)
    # ═══════════════════════════════════════════════════════════════
    if 'Error 127' in error_text:
        suggestions.add("Error 127 = command not found. Install missing build tools.")
        
        # Common missing build tools mapping
        # Format: (search_pattern, package_name, tool_description)
        common_tools = [
            # Documentation tools
            ('makeinfo', 'texinfo', 'makeinfo (documentation generator)'),
            ('help2man', 'help2man', 'help2man (man page generator)'),
            ('doxygen', 'doxygen', 'doxygen (documentation)'),
            
            # File utilities
            ('/usr/bin/file', 'file', 'file (file type detector)'),
            ('file: command not found', 'file', 'file (file type detector)'),
            
            # Autotools
            ('aclocal', 'automake', 'aclocal (automake tool)'),
            ('automake', 'automake', 'automake (build system)'),
            ('autoconf', 'autoconf', 'autoconf (configure generator)'),
            ('autoheader', 'autoconf', 'autoheader (autoconf tool)'),
            ('autom4te', 'autoconf', 'autom4te (autoconf tool)'),
            ('autoreconf', 'autoconf', 'autoreconf (autoconf tool)'),
            ('libtoolize', 'libtool', 'libtoolize (libtool)'),
            ('gtkdocize', 'gtk-doc-tools', 'gtkdocize (GTK docs)'),
            ('intltoolize', 'intltool', 'intltoolize (i18n tool)'),
            
            # Build configuration
            ('pkg-config', 'pkg-config', 'pkg-config (library config)'),
            ('m4', 'm4', 'm4 (macro processor)'),
            
            # Compilers & parsers
            ('yacc', 'bison', 'yacc (parser generator)'),
            ('bison', 'bison', 'bison (parser generator)'),
            ('flex', 'flex', 'flex (lexer generator)'),
            ('lex', 'flex', 'lex (lexer generator)'),
            
            # Assembly
            ('nasm', 'nasm', 'nasm (assembler)'),
            ('yasm', 'yasm', 'yasm (assembler)'),
            
            # Other
            ('gperf', 'gperf', 'gperf (perfect hash generator)'),
            ('swig', 'swig', 'swig (interface generator)'),
        ]
        
        # Check each tool
        found_tools = []
        for pattern, package, description in common_tools:
            if pattern.lower() in error_text.lower():
                suggestions.add(f"Install {description}: apt-get install {package}")
                found_tools.append(package)
        
        # If Error 127 but no specific tool found, give general advice
        if not found_tools:
            suggestions.add("Check which command is missing and install its package")
    
    # ═══════════════════════════════════════════════════════════════
    # Missing header files (.h files)
    # ═══════════════════════════════════════════════════════════════
    if 'No such file or directory' in error_text and '.h' in error_text:
        # Try to extract the specific header file name
        header_patterns = [
            r'fatal error: (.+?\.h):',           # fatal error: openssl/ssl.h:
            r'No such file.*?([a-zA-Z0-9/_-]+\.h)',  # generic .h pattern
        ]
        
        for pattern in header_patterns:
            matches = re.findall(pattern, error_text)
            for header in matches[:3]:  # Limit to first 3 to avoid spam
                header = header.strip()
                # Extract library name from header path
                if '/' in header:
                    lib_name = header.split('/')[0]
                else:
                    lib_name = header.replace('.h', '')
                
                suggestions.add(f"Missing header {header} → try: apt-get install lib{lib_name}-dev")
    
    # ═══════════════════════════════════════════════════════════════
    # Undefined reference (missing libraries at link time)
    # ═══════════════════════════════════════════════════════════════
    # 🆕 CRITICAL: Float16 (half-precision) link errors - MUST CHECK FIRST!
    if '__extendhfsf2' in error_text or '__truncsfhf2' in error_text or '__truncdfhf2' in error_text:
        suggestions.add("🔴 Float16 (half-precision) link error detected!")
        suggestions.add("Solution: Disable Float16 in CMake → cd /repo/build && rm -rf * && cmake .. -DCMAKE_BUILD_TYPE=Release -DGDAL_USE_FLOAT16=OFF && make -j4")
        suggestions.add("Alternative 1: Install libgcc runtime: apt-get install libgcc-s1")
        suggestions.add("Alternative 2: Use GCC instead of Clang: export CC=gcc CXX=g++ && cd /repo/build && rm -rf * && cmake .. && make -j4")
    elif 'undefined reference' in error_text:
        suggestions.add("Linker error: missing library. Check configure options or install -dev packages.")
        
        # Try to extract library name from undefined reference
        # Pattern: undefined reference to `symbol_name'
        lib_patterns = [
            (r'undefined reference to `(\w+)', 'function'),
        ]
        
        for pattern, ref_type in lib_patterns:
            matches = re.findall(pattern, error_text)
            if matches:
                suggestions.add(f"Missing symbols detected. Check library dependencies.")
                break
    
    # ═══════════════════════════════════════════════════════════════
    # Specific library checks (GMP, MPFR, etc.)
    # ═══════════════════════════════════════════════════════════════
    common_libraries = [
        ('GMP', 'gmp.h', 'libgmp-dev', 'GMP (GNU Multiple Precision)'),
        ('MPFR', 'mpfr.h', 'libmpfr-dev', 'MPFR (Multiple Precision Floating-Point)'),
        ('MPC', 'mpc.h', 'libmpc-dev', 'MPC (Multiple Precision Complex)'),
        ('zlib', 'zlib.h', 'zlib1g-dev', 'zlib (compression)'),
        ('OpenSSL', 'openssl/ssl.h', 'libssl-dev', 'OpenSSL (cryptography)'),
        ('curl', 'curl/curl.h', 'libcurl4-openssl-dev', 'libcurl (HTTP client)'),
        ('pthread', 'pthread.h', 'libc6-dev', 'pthread (threading)'),
        ('ncurses', 'ncurses.h', 'libncurses-dev', 'ncurses (terminal UI)'),
        ('readline', 'readline.h', 'libreadline-dev', 'readline (line editing)'),
        ('pcre', 'pcre.h', 'libpcre3-dev', 'PCRE (regex)'),
        ('expat', 'expat.h', 'libexpat1-dev', 'expat (XML parser)'),
        ('libxml2', 'libxml/parser.h', 'libxml2-dev', 'libxml2 (XML)'),
    ]
    
    for lib_name, header, package, description in common_libraries:
        if lib_name in error_text or header in error_text:
            suggestions.add(f"Install {description}: apt-get install {package}")
    
    # ═══════════════════════════════════════════════════════════════
    # Configure errors
    # ═══════════════════════════════════════════════════════════════
    if 'configure: error:' in error_text:
        suggestions.add("Configure failed. Check dependencies and try: apt-cache search <package>")
    
    # ═══════════════════════════════════════════════════════════════
    # Python-specific errors (for hybrid C/Python projects)
    # ═══════════════════════════════════════════════════════════════
    if 'Python.h' in error_text:
        suggestions.add("Install Python dev headers: apt-get install python3-dev")
    
    return list(suggestions)


def should_suggest_single_thread(command, output):
    """
    Determine if we should suggest single-threaded build.
    """
    if 'make' not in command or '-j' not in command:
        return False
    
    # If output is very long and has errors, single thread might help
    if len(output.split('\n')) > 100:
        return True
    
    return False


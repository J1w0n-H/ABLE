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


#!/usr/bin/env python3
# This is $runtest.py$
import subprocess
import argparse
import warnings
import sys
import os
warnings.simplefilter('ignore', FutureWarning)

def check_makefile():
    """Check if Makefile exists and has a test target"""
    if not os.path.exists('/repo/Makefile'):
        return False, "No Makefile found"
    
    try:
        # Check if there's a test target
        result = subprocess.run('make -n test', cwd='/repo', shell=True, capture_output=True, text=True)
        if result.returncode == 0 or 'test' in result.stdout or 'test' in result.stderr:
            return True, "test"
        
        # Check for check target
        result = subprocess.run('make -n check', cwd='/repo', shell=True, capture_output=True, text=True)
        if result.returncode == 0 or 'check' in result.stdout or 'check' in result.stderr:
            return True, "check"
            
        return False, "No test or check target found"
    except Exception as e:
        return False, str(e)

def run_c_tests():
    """
    Run tests for C/C++ projects.
    Following HereNThere philosophy: runtest only VERIFIES.
    
    Assumption: LLM has already successfully built the project using ONE method.
    runtest simply runs the test command for that built state.
    """
    
    # 🥇 If CMake build exists → run ctest/make test
    if os.path.exists('/repo/build/CMakeCache.txt'):
        print('Found existing CMake build. Running tests with CMake...')
        
        # Try ctest first
        result = subprocess.run('ctest --output-on-failure', cwd='/repo/build', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Test output:')
            print(result.stdout)
            sys.exit(0)
        
        # If ctest fails/doesn't exist, try make test
        result = subprocess.run('make test', cwd='/repo/build', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Test output:')
            print(result.stdout)
            sys.exit(0)
        
        # Both failed - show error
        print('Error: Please modify the configuration according to the error messages below. Once all issues are resolved, rerun the tests.')
        print('Stdout:')
        print(result.stdout)
        print('Stderr:')
        print(result.stderr)
        sys.exit(result.returncode)
    
    # 🥈 If Makefile exists → run make test/check (or verify build artifacts)
    elif os.path.exists('/repo/Makefile'):
        has_test, target = check_makefile()
        
        if has_test and target in ['test', 'check']:
            print(f'Running make {target}...')
            result = subprocess.run(f'make {target}', cwd='/repo', shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print('Congratulations, you have successfully configured the environment!')
                print('Test output:')
                print(result.stdout)
                if result.stderr:
                    print('Stderr:')
                    print(result.stderr)
                sys.exit(0)
            else:
                print('Error: Please modify the configuration according to the error messages below. Once all issues are resolved, rerun the tests.')
                print('Stdout:')
                print(result.stdout)
                print('Stderr:')
                print(result.stderr)
                sys.exit(result.returncode)
        else:
            # No test target, verify build artifacts exist
            print('No test target found. Verifying build artifacts...')
            result = subprocess.run('find /repo -name "*.o" -o -name "*.so" -o -type f -executable 2>/dev/null | head -5', 
                                  shell=True, capture_output=True, text=True)
            
            if result.stdout.strip():
                print('Build artifacts found. Environment is correctly configured.')
                print('Congratulations, you have successfully configured the environment!')
                sys.exit(0)
            else:
                print('Error: Makefile exists but no build artifacts found.')
                print('Please ensure you have run: make')
                sys.exit(1)
    
    # ❌ No build found - LLM hasn't built the project yet
    else:
        print('Error: No build artifacts found.')
        print('Please build the project first before running tests.')
        print('')
        
        # Provide helpful hints based on what exists
        if os.path.exists('/repo/configure'):
            print('This is an autoconf project. Please run:')
            print('  cd /repo && ./configure && make')
        elif os.path.exists('/repo/CMakeLists.txt'):
            print('This is a CMake project. Please run:')
            print('  mkdir /repo/build && cd /repo/build && cmake .. && make')
        elif os.path.exists('/repo/Makefile'):
            print('Makefile found. Please run:')
            print('  cd /repo && make')
        else:
            # Really simple projects (like hello.c with just .c files)
            print('No build system detected (no Makefile or CMakeLists.txt).')
            print('For this simple project, the environment is considered correctly configured.')
            print('Congratulations, you have successfully configured the environment!')
            sys.exit(0)
        
        sys.exit(1)

if __name__ == '__main__':
    run_c_tests()


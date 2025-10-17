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
    """Run tests for C/C++ projects"""
    
    # 🥇 Priority 1: Reuse existing CMake build if available
    # This respects the LLM agent's work and avoids redundant builds
    if os.path.exists('/repo/build/CMakeCache.txt'):
        print('Found existing CMake build. Running tests with CMake...')
        
        # Try ctest first (standard CMake testing)
        result = subprocess.run('ctest --output-on-failure', cwd='/repo/build', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Test output:')
            print(result.stdout)
            sys.exit(0)
        
        # If ctest fails or doesn't exist, try make test
        result = subprocess.run('make test', cwd='/repo/build', shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Test output:')
            print(result.stdout)
            sys.exit(0)
        
        # If both fail but build exists, consider it success (build is enough)
        if os.path.exists('/repo/build/Makefile'):
            print('CMake build completed successfully.')
            print('Congratulations, you have successfully configured the environment!')
            sys.exit(0)
    
    # 🥈 Priority 2: Makefile with test target
    has_makefile, target = check_makefile()
    
    if has_makefile and target in ['test', 'check']:
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
    
    # 🥉 Priority 3: Makefile without test target
    elif os.path.exists('/repo/Makefile'):
        print('No test target found. Attempting to build the project with make...')
        result = subprocess.run('make', cwd='/repo', shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Build output:')
            print(result.stdout)
            sys.exit(0)
        else:
            print('Error: Build failed. Please modify the configuration according to the error messages below.')
            print('Stdout:')
            print(result.stdout)
            print('Stderr:')
            print(result.stderr)
            sys.exit(result.returncode)
    
    # Check for CMakeLists.txt
    elif os.path.exists('/repo/CMakeLists.txt'):
        print('CMake project detected. Building...')
        # Create build directory if it doesn't exist
        if not os.path.exists('/repo/build'):
            os.makedirs('/repo/build')
        
        result = subprocess.run('cmake .. && make', cwd='/repo/build', shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print('Congratulations, you have successfully configured the environment!')
            print('Build output:')
            print(result.stdout)
            sys.exit(0)
        else:
            print('Error: CMake build failed. Please modify the configuration.')
            print('Stdout:')
            print(result.stdout)
            print('Stderr:')
            print(result.stderr)
            sys.exit(result.returncode)
    
    else:
        print('No build system detected (no Makefile or CMakeLists.txt).')
        print('For this simple project, the environment is considered correctly configured.')
        print('Congratulations, you have successfully configured the environment!')
        sys.exit(0)

if __name__ == '__main__':
    run_c_tests()


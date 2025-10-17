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
import sys
import os

def run_cmake():
    """Build C project using cmake (configure + make)"""
    try:
        # Configure with cmake
        print("Running cmake configuration...")
        configure_result = subprocess.run(['cmake', '.'], cwd='/repo', check=True, capture_output=True, text=True, timeout=300)
        print("CMake configuration successful!")
        print(configure_result.stdout)
        
        # Build with make
        print("Running make build...")
        build_result = subprocess.run(['make'], cwd='/repo', check=True, capture_output=True, text=True, timeout=300)
        print("CMake build completed successfully!")
        print(build_result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print('CMake build failed!')
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print('CMake build timed out after 5 minutes!')
        return False
    except Exception as e:
        print(f'Unexpected error during cmake build: {e}')
        return False

if __name__ == '__main__':
    success = run_cmake()
    sys.exit(0 if success else 1)

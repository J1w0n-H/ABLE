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
import glob

def run_gcc():
    """Compile C project directly with gcc"""
    try:
        # Find all C files in the repository
        c_files = glob.glob('/repo/*.c')
        if not c_files:
            print("No C files found in /repo directory!")
            return False
        
        print(f"Found C files: {c_files}")
        
        # Compile with gcc
        cmd = ['gcc', '-o', 'hello'] + c_files
        result = subprocess.run(cmd, cwd='/repo', check=True, capture_output=True, text=True, timeout=300)
        
        print('GCC compilation completed successfully!')
        print(result.stdout)
        
        # Check if executable was created
        if os.path.exists('/repo/hello'):
            print("Executable 'hello' created successfully!")
        else:
            print("Warning: Executable not found after compilation")
            
        return True
        
    except subprocess.CalledProcessError as e:
        print('GCC compilation failed!')
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print('GCC compilation timed out after 5 minutes!')
        return False
    except Exception as e:
        print(f'Unexpected error during GCC compilation: {e}')
        return False

if __name__ == '__main__':
    success = run_gcc()
    sys.exit(0 if success else 1)

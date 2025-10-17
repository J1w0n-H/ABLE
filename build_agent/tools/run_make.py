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

def run_make():
    """Build C project using make command"""
    try:
        result = subprocess.run(['make'], cwd='/repo', check=True, capture_output=True, text=True, timeout=300)
        print('Make build completed successfully!')
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print('Make build failed!')
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print('Make build timed out after 5 minutes!')
        return False
    except Exception as e:
        print(f'Unexpected error during make build: {e}')
        return False

if __name__ == '__main__':
    success = run_make()
    sys.exit(0 if success else 1)

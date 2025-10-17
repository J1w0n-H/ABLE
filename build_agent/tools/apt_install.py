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
import argparse

def apt_install(package_name):
    """Install system packages using apt-get"""
    try:
        # Update package list
        print(f"Updating package list...")
        update_result = subprocess.run(['apt-get', 'update'], check=True, capture_output=True, text=True, timeout=300)
        
        # Install package
        print(f"Installing package: {package_name}")
        install_result = subprocess.run(['apt-get', 'install', '-y', package_name], check=True, capture_output=True, text=True, timeout=300)
        
        print(f'Package {package_name} installed successfully!')
        print(install_result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f'Failed to install package {package_name}!')
        print(f"Error: {e}")
        print(f"Stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print(f'Package installation timed out after 5 minutes!')
        return False
    except Exception as e:
        print(f'Unexpected error during package installation: {e}')
        return False

def main():
    parser = argparse.ArgumentParser(description='Install system packages')
    parser.add_argument('-p', '--package', required=True, help='Package name to install')
    
    args = parser.parse_args()
    success = apt_install(args.package)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

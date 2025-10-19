#!/usr/bin/env python3
"""
System Package Installation Tool
Installs system packages using apt-get
"""

import subprocess
import sys
import argparse

def apt_install(package_name):
    """Install system package using apt-get"""
    try:
        print(f"📦 Installing package: {package_name}")
        
        # Update package list and install package
        cmd = f'apt-get update && apt-get install -y {package_name}'
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✅ Package {package_name} installed successfully!")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_name}!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Install system package')
    parser.add_argument('package_name', help='Name of the package to install')
    args = parser.parse_args()
    
    success = apt_install(args.package_name)
    sys.exit(0 if success else 1)

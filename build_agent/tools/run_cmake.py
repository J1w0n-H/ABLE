#!/usr/bin/env python3
"""
C CMake Build Tool
Executes 'cmake' configuration and 'make' build for C projects
"""

import subprocess
import sys
import os

def run_cmake():
    """Execute cmake configuration and make build for C project"""
    try:
        print("🔧 Running cmake configuration...")
        # Configure with cmake
        subprocess.run(
            'cmake .', 
            cwd='/repo', 
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ CMake configuration completed!")
        
        print("🔨 Running make build...")
        # Build with make
        result = subprocess.run(
            'make', 
            cwd='/repo', 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ CMake build completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ CMake build failed!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_cmake()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
C GCC Compilation Tool
Compiles C projects directly with gcc
"""

import subprocess
import sys
import os
import glob

def run_gcc():
    """Compile C project directly with gcc"""
    try:
        print("🔍 Finding C source files...")
        # Find all .c files in the repo
        c_files = glob.glob('/repo/**/*.c', recursive=True)
        
        if not c_files:
            print("❌ No C source files found!")
            return False
        
        print(f"📁 Found C files: {c_files}")
        
        # Compile with gcc
        cmd = ['gcc', '-o', 'hello'] + c_files
        print(f"🔨 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd='/repo',
            check=True,
            capture_output=True,
            text=True
        )
        
        print("✅ GCC compilation completed successfully!")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ GCC compilation failed!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_gcc()
    sys.exit(0 if success else 1)

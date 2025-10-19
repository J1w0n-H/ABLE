#!/usr/bin/env python3
"""
C Make Build Tool
Executes 'make' command for C projects
"""

import subprocess
import sys
import os

def run_make():
    """Execute make command for C project"""
    try:
        print("🔨 Running make command...")
        result = subprocess.run(
            'make', 
            cwd='/repo', 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ Make build completed successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Make build failed!")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_make()
    sys.exit(0 if success else 1)

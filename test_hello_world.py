#!/usr/bin/env python3
"""
Simple test script for ARVO2.0 C build agent
Creates a minimal Hello World C project and tests the build process
"""

import os
import subprocess
import tempfile
import shutil

def create_hello_world_repo():
    """Create a simple Hello World C repository for testing"""
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp(prefix="hello-world-c-")
    print(f"Creating test repository at: {temp_dir}")
    
    # Create main.c
    main_c_content = '''#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
'''
    
    with open(os.path.join(temp_dir, "main.c"), "w") as f:
        f.write(main_c_content)
    
    # Create Makefile
    makefile_content = '''hello: main.c
	gcc -o hello main.c

clean:
	rm -f hello

.PHONY: clean
'''
    
    with open(os.path.join(temp_dir, "Makefile"), "w") as f:
        f.write(makefile_content)
    
    # Create README.md
    readme_content = '''# Hello World C

A simple C program that prints "Hello, World!"

## Build

```bash
make
```

## Run

```bash
./hello
```

## Clean

```bash
make clean
```
'''
    
    with open(os.path.join(temp_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=temp_dir, check=True)
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit: Hello World C"], cwd=temp_dir, check=True)
    
    # Get commit SHA
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=temp_dir, capture_output=True, text=True, check=True)
    commit_sha = result.stdout.strip()
    
    print(f"Created Hello World C repository")
    print(f"Commit SHA: {commit_sha}")
    print(f"Files created:")
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            print(f"  {os.path.join(root, file)}")
    
    return temp_dir, commit_sha

def test_arvo2_build(repo_path, commit_sha):
    """Test ARVO2.0 build process"""
    
    print(f"\nTesting ARVO2.0 build process...")
    
    # Get absolute path to ARVO2.0
    arvo2_path = "/root/Git/ARVO2.0"
    
    # Run ARVO2.0
    cmd = [
        "python3", "build_agent/main.py",
        "test/hello-world-c",  # full_name
        commit_sha,           # sha
        arvo2_path            # root_path
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print(f"Working directory: {arvo2_path}")
    
    try:
        result = subprocess.run(cmd, cwd=arvo2_path, capture_output=True, text=True, timeout=600)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Build process timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"Error running ARVO2.0: {e}")
        return False

def main():
    """Main test function"""
    print("=== ARVO2.0 C Build Agent Test ===")
    
    # Create test repository
    repo_path, commit_sha = create_hello_world_repo()
    
    try:
        # Test build process
        success = test_arvo2_build(repo_path, commit_sha)
        
        if success:
            print("\n✅ Test PASSED: ARVO2.0 successfully built Hello World C project!")
        else:
            print("\n❌ Test FAILED: ARVO2.0 failed to build Hello World C project")
            
    finally:
        # Cleanup
        print(f"\nCleaning up test repository: {repo_path}")
        shutil.rmtree(repo_path)

if __name__ == "__main__":
    main()

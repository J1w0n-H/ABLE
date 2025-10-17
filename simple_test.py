#!/usr/bin/env python3
"""
Simple test without LLM - manually test sandbox and build tools
"""

import os
import sys
import subprocess

# Add build_agent to path
sys.path.insert(0, '/root/Git/ARVO2.0/build_agent')

from utils.sandbox import Sandbox

def test_sandbox_and_build():
    """Test sandbox creation and C build"""
    print("=== Testing ARVO2.0 Sandbox and C Build ===\n")
    
    # Create a simple test repository
    test_dir = "/tmp/test-c-build"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create main.c
    with open(f"{test_dir}/main.c", "w") as f:
        f.write('''#include <stdio.h>

int main() {
    printf("Hello from ARVO2.0!\\n");
    return 0;
}
''')
    
    # Create Makefile
    with open(f"{test_dir}/Makefile", "w") as f:
        f.write('''hello: main.c
\tgcc -o hello main.c

clean:
\trm -f hello
''')
    
    print("✓ Created test C project at:", test_dir)
    print(f"  - main.c")
    print(f"  - Makefile\n")
    
    # Create sandbox
    print("Creating sandbox...")
    sandbox = Sandbox("gcr.io/oss-fuzz-base/base-builder", "test/simple-c", "/root/Git/ARVO2.0")
    
    # Prepare repo structure
    os.makedirs("/root/Git/ARVO2.0/utils/repo/test/simple-c/repo", exist_ok=True)
    os.system(f"cp {test_dir}/* /root/Git/ARVO2.0/utils/repo/test/simple-c/repo/")
    
    print("✓ Sandbox prepared\n")
    
    # Start container
    print("Starting Docker container...")
    session = sandbox.start_container()
    print("✓ Container started\n")
    
    # Test listing files
    print("Listing files in /repo...")
    success, output = session.execute_simple("ls -la /repo")
    print(f"Output:\n{output}\n")
    
    # Test make build
    print("Running make build...")
    success, output = session.execute_simple("run_make")
    print(f"Build success: {success}")
    print(f"Output:\n{output}\n")
    
    # Check if executable was created
    print("Checking for executable...")
    success, output = session.execute_simple("ls -la /repo/hello")
    print(f"Output:\n{output}\n")
    
    # Try to run the executable
    print("Running the executable...")
    success, output = session.execute_simple("cd /repo && ./hello")
    print(f"Execution success: {success}")
    print(f"Output:\n{output}\n")
    
    # Stop container
    print("Stopping container...")
    commands = sandbox.stop_container()
    print(f"✓ Container stopped\n")
    
    print(f"Command history ({len(commands)} commands):")
    for cmd in commands:
        print(f"  - {cmd['command']}")
    
    print("\n=== Test Complete ===")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_dir)
    shutil.rmtree("/root/Git/ARVO2.0/utils/repo/test", ignore_errors=True)

if __name__ == "__main__":
    test_sandbox_and_build()

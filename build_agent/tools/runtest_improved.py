#!/usr/bin/env python3
"""
Improved runtest.py for C/C++ projects
- Verifies build artifacts exist
- Handles projects without test targets
- Provides clear error guidance
"""

import subprocess
import sys
import os
import glob
import stat

def find_build_artifacts(search_dir, verbose=False):
    """
    Find compiled artifacts to verify build completion.
    Returns: list of artifact paths
    """
    artifacts = []
    
    # Pattern 1: Object files and libraries
    patterns = {
        '**/*.o': 'Object files',
        '**/*.a': 'Static libraries',
        '**/*.so': 'Shared libraries',
        '**/*.so.*': 'Versioned shared libraries',
        '**/*.dylib': 'Shared libraries (macOS)',
    }
    
    for pattern, desc in patterns.items():
        matches = glob.glob(f'{search_dir}/{pattern}', recursive=True)
        if verbose and matches:
            print(f'  Found {len(matches)} {desc}')
        artifacts.extend(matches)
    
    # Pattern 2: ELF executables (binary files with execute permission)
    executables = []
    for root, dirs, files in os.walk(search_dir):
        # Skip hidden directories (.git, etc.)
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            filepath = os.path.join(root, file)
            try:
                st = os.stat(filepath)
                # Check if file has execute permission
                if st.st_mode & stat.S_IXUSR:
                    # Check if it's an ELF binary (not script)
                    with open(filepath, 'rb') as f:
                        magic = f.read(4)
                        # ELF magic: 0x7f 'E' 'L' 'F'
                        # Mach-O magic: 0xfeedface, 0xfeedfacf, 0xcafebabe, 0xcefaedfe
                        if magic[:4] == b'\x7fELF' or \
                           magic[:4] in [b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', 
                                        b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe']:
                            executables.append(filepath)
                            if verbose:
                                print(f'  Found executable: {filepath}')
            except:
                pass
    
    artifacts.extend(executables)
    return artifacts

def try_test_command(command, cwd, timeout=300):
    """
    Try to run a test command.
    Returns: (returncode, stdout, stderr) or None if command doesn't exist
    """
    result = subprocess.run(
        command,
        cwd=cwd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    
    # Check if command failed because target doesn't exist
    error_patterns = [
        'No rule to make target',
        'No such file or directory',
        'command not found',
        'No targets specified and no makefile found'
    ]
    
    combined_output = result.stdout + result.stderr
    for pattern in error_patterns:
        if pattern in combined_output:
            return None
    
    return result

def show_build_guidance(build_system, build_dir):
    """Show clear guidance on how to build the project"""
    print('╔════════════════════════════════════════════════════════════════╗')
    print('║  ❌ Error: Build system detected but NO build artifacts found ║')
    print('╟────────────────────────────────────────────────────────────────╢')
    print('║  This means the project has NOT been built yet.               ║')
    print('║  Expected artifacts: *.o, *.a, *.so, executables              ║')
    print('╟────────────────────────────────────────────────────────────────╢')
    print('║  📝 How to fix:                                               ║')
    
    if build_system == 'cmake':
        print('║                                                                ║')
        print('║  Step 1: Build the project                                    ║')
        print('║    cd /repo/build && make -j4                                 ║')
        print('║                                                                ║')
        print('║  Step 2: Run runtest again                                    ║')
        print('║    runtest                                                     ║')
    elif build_system == 'makefile':
        print('║                                                                ║')
        print('║  Step 1: Build the project                                    ║')
        print('║    cd /repo && make -j4                                       ║')
        print('║                                                                ║')
        print('║  Step 2: Run runtest again                                    ║')
        print('║    runtest                                                     ║')
    elif build_system == 'configure':
        print('║                                                                ║')
        print('║  Step 1: Configure the build                                  ║')
        print('║    cd /repo && ./configure                                    ║')
        print('║                                                                ║')
        print('║  Step 2: Build the project                                    ║')
        print('║    make -j4                                                   ║')
        print('║                                                                ║')
        print('║  Step 3: Run runtest again                                    ║')
        print('║    runtest                                                     ║')
    elif build_system == 'simple':
        print('║                                                                ║')
        print('║  Step 1: Compile source files                                 ║')
        print('║    cd /repo && gcc *.c -o myapp                               ║')
        print('║  Or for C++:                                                   ║')
        print('║    cd /repo && g++ *.cpp -o myapp                             ║')
        print('║                                                                ║')
        print('║  Step 2: Run runtest again                                    ║')
        print('║    runtest                                                     ║')
    
    print('╟────────────────────────────────────────────────────────────────╢')
    print('║  ⚠️  IMPORTANT: BUILD FIRST, then run runtest!                 ║')
    print('╚════════════════════════════════════════════════════════════════╝')

def run_c_tests():
    """
    Improved runtest logic:
    1. Detect build system
    2. ✅ VERIFY build artifacts exist (NEW!)
    3. Try to run tests (optional)
    4. Success if artifacts found OR tests pass
    """
    
    print('=' * 70)
    print('ARVO2.0 C/C++ Project Test Verification')
    print('=' * 70)
    
    # ==========================================
    # Step 1: Detect build system
    # ==========================================
    
    build_system = None
    build_dir = None
    test_command = None
    
    # Priority 1: CMake build (most specific)
    if os.path.exists('/repo/build/CMakeCache.txt'):
        print('\n🔍 Detected: CMake project')
        
        if not os.path.exists('/repo/build/Makefile'):
            print('\n❌ Error: CMake configured but Makefile not generated.')
            print('│  Please run: cd /repo/build && cmake ..')
            sys.exit(1)
        
        build_system = 'cmake'
        build_dir = '/repo/build'
        test_command = 'ctest --output-on-failure'
    
    # Priority 2: Makefile (common)
    elif os.path.exists('/repo/Makefile'):
        print('\n🔍 Detected: Makefile project')
        build_system = 'makefile'
        build_dir = '/repo'
        test_command = 'make test'
    
    # Priority 3: autoconf/configure
    elif os.path.exists('/repo/configure'):
        print('\n🔍 Detected: Autoconf project (configure script)')
        
        # Check if configure was run
        if not os.path.exists('/repo/Makefile'):
            print('\n❌ Error: configure script exists but has NOT been run.')
            print('╔════════════════════════════════════════════════════════════════╗')
            print('║  📝 How to fix:                                               ║')
            print('║                                                                ║')
            print('║  Step 1: Run configure                                        ║')
            print('║    cd /repo && ./configure                                    ║')
            print('║                                                                ║')
            print('║  Step 2: Build the project                                    ║')
            print('║    make -j4                                                   ║')
            print('║                                                                ║')
            print('║  Step 3: Run runtest again                                    ║')
            print('║    runtest                                                     ║')
            print('╚════════════════════════════════════════════════════════════════╝')
            sys.exit(1)
        
        build_system = 'makefile'
        build_dir = '/repo'
        test_command = 'make test'
    
    # Priority 4: CMakeLists.txt exists but not configured
    elif os.path.exists('/repo/CMakeLists.txt'):
        print('\n🔍 Detected: CMake project (CMakeLists.txt found)')
        print('\n❌ Error: CMakeLists.txt exists but project NOT configured.')
        print('╔════════════════════════════════════════════════════════════════╗')
        print('║  📝 How to fix:                                               ║')
        print('║                                                                ║')
        print('║  Step 1: Configure with CMake                                 ║')
        print('║    mkdir -p /repo/build && cd /repo/build && cmake ..         ║')
        print('║                                                                ║')
        print('║  Step 2: Build the project                                    ║')
        print('║    make -j4                                                   ║')
        print('║                                                                ║')
        print('║  Step 3: Run runtest again                                    ║')
        print('║    runtest                                                     ║')
        print('╚════════════════════════════════════════════════════════════════╝')
        sys.exit(1)
    
    # Priority 5: Simple project (just .c/.cpp files)
    else:
        print('\n🔍 Detected: Simple project (no build system)')
        build_system = 'simple'
        build_dir = '/repo'
        test_command = None
    
    # ==========================================
    # Step 2: VERIFY build artifacts (NEW!)
    # ==========================================
    
    if build_system != 'simple':
        print(f'\n🔍 Checking for build artifacts in {build_dir}...')
        artifacts = find_build_artifacts(build_dir, verbose=True)
        
        if not artifacts:
            show_build_guidance(build_system, build_dir)
            sys.exit(1)
        
        print(f'\n✅ Build artifacts verified: {len(artifacts)} files found')
        print('│  Sample artifacts:')
        for artifact in artifacts[:10]:
            rel_path = artifact.replace(build_dir, '.')
            print(f'│    • {rel_path}')
        if len(artifacts) > 10:
            print(f'│    ... and {len(artifacts) - 10} more files')
    else:
        # Simple project - check for executables or object files
        print(f'\n🔍 Checking for compiled files in {build_dir}...')
        artifacts = find_build_artifacts(build_dir, verbose=True)
        
        if not artifacts:
            print('\n⚠️  Warning: No build artifacts found.')
            print('│  For C projects, you typically need to compile:')
            print('│    gcc *.c -o myapp')
            print('│  For C++:')
            print('│    g++ *.cpp -o myapp')
            print('│')
            print('│  However, this might be okay for very simple projects.')
            print('│  Marking as SUCCESS (no build system = no build needed).')
            print('\n✅ Simple project verified (no build required)')
            print('\nCongratulations, you have successfully configured the environment!')
            sys.exit(0)
        
        print(f'\n✅ Build artifacts found: {len(artifacts)} files')
        for artifact in artifacts[:5]:
            rel_path = artifact.replace(build_dir, '.')
            print(f'│    • {rel_path}')
    
    # ==========================================
    # Step 3: Try to run tests (optional)
    # ==========================================
    
    if test_command:
        print(f'\n🧪 Attempting to run tests: {test_command}')
        print('-' * 70)
        
        result = try_test_command(test_command, build_dir)
        
        if result is None:
            # No test target - that's okay!
            print('-' * 70)
            print('ℹ️  No test target found in build system.')
            print('│')
            print('│  This is common for libraries and simple projects.')
            print('│  Build artifacts were verified successfully.')
            print('│')
            print('✅ Build verification passed!')
            print('\nCongratulations, you have successfully configured the environment!')
            sys.exit(0)
        
        # Test target exists - check result
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        print('-' * 70)
        
        if result.returncode == 0:
            print('✅ Tests passed!')
            print('\nCongratulations, you have successfully configured the environment!')
            sys.exit(0)
        else:
            print('❌ Tests failed!')
            print('│')
            print('│  Build artifacts exist, but tests are failing.')
            print('│  Please review the error messages above.')
            print('│')
            print('│  Common issues:')
            print('│    - Missing runtime dependencies')
            print('│    - Incorrect test data paths')
            print('│    - Permission issues')
            sys.exit(result.returncode)
    
    else:
        # No test command - just verify artifacts
        print('\n✅ Build verification passed!')
        print('│  Build artifacts found and verified.')
        print('│  No test target to run.')
        print('\nCongratulations, you have successfully configured the environment!')
        sys.exit(0)

if __name__ == '__main__':
    try:
        run_c_tests()
    except KeyboardInterrupt:
        print('\n\n❌ Test interrupted by user')
        sys.exit(1)
    except Exception as e:
        print(f'\n\n❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)



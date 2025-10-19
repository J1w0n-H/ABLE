#!/usr/bin/env python3
# build.py - C/C++ project build tool
# Copyright (2025) Bytedance Ltd. and/or its affiliates

import subprocess
import sys
import os

def build_project():
    """
    Build C/C++ project by detecting and using the appropriate build system.
    
    This tool MUST be run after installing dependencies and BEFORE runtest.
    
    Supported build systems:
    1. autoconf (./configure + make)
    2. CMake (cmake + make)
    3. Plain Makefile (make)
    
    Returns:
        0 on success, non-zero on failure
    """
    
    print('=' * 70)
    print('🔨 Starting C/C++ project build...')
    print('=' * 70)
    
    # ==========================================
    # Priority 1: autoconf (./configure + make)
    # ==========================================
    if os.path.exists('/repo/configure'):
        print('\n📋 Detected: autoconf project (./configure script found)')
        print('Building with: ./configure && make')
        print('-' * 70)
        
        # Step 1: Run ./configure
        print('\n[1/2] Running ./configure...')
        result = subprocess.run(
            './configure',
            cwd='/repo',
            shell=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes
        )
        
        if result.returncode != 0:
            print('❌ ./configure failed!')
            print('\nStderr:')
            print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
            print('\nStdout:')
            print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
            sys.exit(result.returncode)
        
        print('✅ ./configure completed successfully')
        
        # Step 2: Run make
        print('\n[2/2] Running make...')
        result = subprocess.run(
            'make',
            cwd='/repo',
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes
        )
        
        if result.returncode != 0:
            print('❌ make failed!')
            print('\nStderr:')
            print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
            print('\nStdout:')
            print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
            sys.exit(result.returncode)
        
        print('✅ make completed successfully')
        print('\n' + '=' * 70)
        print('🎉 Build successful! (autoconf)')
        print('=' * 70)
        print('ℹ️  Makefile generated at: /repo/Makefile')
        print('ℹ️  You can now run: runtest')
        sys.exit(0)
    
    # ==========================================
    # Priority 2: CMake (cmake + make)
    # ==========================================
    elif os.path.exists('/repo/CMakeLists.txt'):
        print('\n📋 Detected: CMake project (CMakeLists.txt found)')
        
        # Check if already configured
        if os.path.exists('/repo/build/CMakeCache.txt'):
            print('ℹ️  CMake already configured (build/ directory exists)')
            print('Building with: make')
            print('-' * 70)
            
            # Just run make
            print('\n[1/1] Running make...')
            result = subprocess.run(
                'make',
                cwd='/repo/build',
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                print('❌ make failed!')
                print('\nStderr:')
                print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
                sys.exit(result.returncode)
            
            print('✅ make completed successfully')
            print('\n' + '=' * 70)
            print('🎉 Build successful! (CMake)')
            print('=' * 70)
            print('ℹ️  Build directory: /repo/build')
            print('ℹ️  You can now run: runtest')
            sys.exit(0)
        else:
            print('Building with: mkdir build && cd build && cmake .. && make')
            print('-' * 70)
            
            # Step 1: Create build directory
            print('\n[1/3] Creating build directory...')
            os.makedirs('/repo/build', exist_ok=True)
            print('✅ Build directory created')
            
            # Step 2: Run cmake
            print('\n[2/3] Running cmake ...')
            result = subprocess.run(
                'cmake ..',
                cwd='/repo/build',
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                print('❌ cmake failed!')
                print('\nStderr:')
                print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
                print('\nStdout:')
                print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
                sys.exit(result.returncode)
            
            print('✅ cmake completed successfully')
            
            # Step 3: Run make
            print('\n[3/3] Running make...')
            result = subprocess.run(
                'make',
                cwd='/repo/build',
                shell=True,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode != 0:
                print('❌ make failed!')
                print('\nStderr:')
                print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
                sys.exit(result.returncode)
            
            print('✅ make completed successfully')
            print('\n' + '=' * 70)
            print('🎉 Build successful! (CMake)')
            print('=' * 70)
            print('ℹ️  Build directory: /repo/build')
            print('ℹ️  CMakeCache.txt: /repo/build/CMakeCache.txt')
            print('ℹ️  You can now run: runtest')
            sys.exit(0)
    
    # ==========================================
    # Priority 3: Plain Makefile (make)
    # ==========================================
    elif os.path.exists('/repo/Makefile'):
        print('\n📋 Detected: Makefile project (Makefile found)')
        print('Building with: make')
        print('-' * 70)
        
        print('\n[1/1] Running make...')
        result = subprocess.run(
            'make',
            cwd='/repo',
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode != 0:
            print('❌ make failed!')
            print('\nStderr:')
            print(result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr)
            print('\nStdout:')
            print(result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout)
            sys.exit(result.returncode)
        
        print('✅ make completed successfully')
        print('\n' + '=' * 70)
        print('🎉 Build successful! (Makefile)')
        print('=' * 70)
        print('ℹ️  You can now run: runtest')
        sys.exit(0)
    
    # ==========================================
    # No build system detected
    # ==========================================
    else:
        print('\n⚠️  No build system detected')
        print('-' * 70)
        
        # Provide hints
        if os.path.exists('/repo/configure.ac'):
            print('❌ Error: configure.ac found but ./configure script missing')
            print('\nℹ️  This is an autoconf project. You may need to run:')
            print('   cd /repo && autoreconf -i')
            print('   cd /repo && ./configure')
            print('   make')
            sys.exit(1)
        elif os.path.exists('/repo/Makefile.am'):
            print('❌ Error: Makefile.am found but Makefile missing')
            print('\nℹ️  This is an automake project. You may need to run:')
            print('   cd /repo && autoreconf -i')
            print('   cd /repo && ./configure')
            sys.exit(1)
        else:
            # Very simple project - no build needed
            print('ℹ️  Simple project detected (no Makefile or CMakeLists.txt)')
            print('ℹ️  No build step needed for this project')
            print('\n' + '=' * 70)
            print('🎉 No build required!')
            print('=' * 70)
            print('ℹ️  You can run: runtest')
            sys.exit(0)

if __name__ == '__main__':
    try:
        build_project()
    except subprocess.TimeoutExpired:
        print('\n❌ Build timed out!')
        print('ℹ️  The build process took too long and was terminated.')
        sys.exit(124)
    except KeyboardInterrupt:
        print('\n❌ Build interrupted by user')
        sys.exit(130)
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')
        sys.exit(1)


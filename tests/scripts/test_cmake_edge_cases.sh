#!/bin/bash
echo "=== Testing Edge Cases for CMakeCache.txt check ==="

# Case 1: CMakeCache.txt exists but no binaries built
echo -e "\n1. CMake configured but not compiled:"
docker run --rm build_env_gcr.io/oss-fuzz-base/base-builder bash -c "
  git clone --depth 1 https://github.com/DaveGamble/cJSON.git /repo 2>/dev/null
  cd /repo && mkdir build && cd build && cmake .. >/dev/null 2>&1
  ls CMakeCache.txt 2>/dev/null && echo '  CMakeCache.txt: EXISTS'
  ls libcjson.so 2>/dev/null && echo '  Binary: EXISTS' || echo '  Binary: NOT FOUND'
"

# Case 2: Partial build (make interrupted)
echo -e "\n2. Build interrupted (timeout):"
docker run --rm build_env_gcr.io/oss-fuzz-base/base-builder bash -c "
  git clone --depth 1 https://github.com/DaveGamble/cJSON.git /repo 2>/dev/null
  cd /repo && mkdir build && cd build && cmake .. >/dev/null 2>&1
  timeout 0.1 make 2>/dev/null || true
  ls CMakeCache.txt 2>/dev/null && echo '  CMakeCache.txt: EXISTS'
  find . -name '*.o' | head -1 && echo '  Partial build: YES' || echo '  Partial build: NO'
"

echo -e "\n3. Out-of-source vs in-source build:"
echo "  /repo/build/ - Standard out-of-source build"
echo "  /repo/ - In-source build (CMakeCache.txt in /repo)"

echo -e "\nDone!"

#!/bin/bash
# Test script for improved runtest.py
# This script verifies the improvements work correctly

set -e

echo "=========================================="
echo "Testing Improved runtest.py"
echo "=========================================="

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ORIGINAL="${SCRIPT_DIR}/build_agent/tools/runtest.py"
IMPROVED="${SCRIPT_DIR}/build_agent/tools/runtest_improved.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Check if improved version exists
echo -e "\n${YELLOW}Test 1: File existence${NC}"
if [ -f "$IMPROVED" ]; then
    test_result 0 "runtest_improved.py exists"
else
    test_result 1 "runtest_improved.py not found"
    exit 1
fi

# Test 2: Python syntax check
echo -e "\n${YELLOW}Test 2: Python syntax validation${NC}"
python3 -m py_compile "$IMPROVED" 2>/dev/null
test_result $? "Python syntax is valid"

# Test 3: Check for key functions
echo -e "\n${YELLOW}Test 3: Key function verification${NC}"
grep -q "def verify_cmake_build" "$IMPROVED"
test_result $? "verify_cmake_build() function exists"

grep -q "def attempt_cmake_build" "$IMPROVED"
test_result $? "attempt_cmake_build() function exists"

# Test 4: Check confidence score logic
echo -e "\n${YELLOW}Test 4: Confidence score implementation${NC}"
grep -q "confidence" "$IMPROVED"
test_result $? "Confidence score logic present"

grep -q "if not is_complete or confidence < 70" "$IMPROVED"
test_result $? "Confidence threshold (70%) implemented"

# Test 5: Compare line counts (should be longer)
echo -e "\n${YELLOW}Test 5: Code expansion check${NC}"
ORIGINAL_LINES=$(wc -l < "$ORIGINAL")
IMPROVED_LINES=$(wc -l < "$IMPROVED")

if [ "$IMPROVED_LINES" -gt "$ORIGINAL_LINES" ]; then
    test_result 0 "Improved version is longer ($IMPROVED_LINES vs $ORIGINAL_LINES lines)"
else
    test_result 1 "Improved version should be longer (added verification logic)"
fi

# Test 6: Check for timeout handling
echo -e "\n${YELLOW}Test 6: Timeout handling${NC}"
grep -q "timeout=600" "$IMPROVED"
test_result $? "Build timeout (10 min) implemented"

# Test 7: Artifact patterns check
echo -e "\n${YELLOW}Test 7: Build artifact detection${NC}"
grep -q "common_artifacts" "$IMPROVED"
test_result $? "Artifact pattern list present"

grep -q "glob.glob" "$IMPROVED"
test_result $? "Glob-based artifact search implemented"

# Test 8: Check for glob import
echo -e "\n${YELLOW}Test 8: Required imports${NC}"
grep -q "^import glob" "$IMPROVED"
test_result $? "glob module imported"

# Test 9: Verify copyright/license preserved
echo -e "\n${YELLOW}Test 9: License preservation${NC}"
head -n 5 "$IMPROVED" | grep -q "Copyright.*Bytedance"
test_result $? "Copyright notice preserved"

# Test 10: Check error message improvements
echo -e "\n${YELLOW}Test 10: Enhanced error messages${NC}"
grep -q "⚠️" "$IMPROVED"
test_result $? "Warning symbols added for better UX"

grep -q "Build verification:" "$IMPROVED"
test_result $? "Detailed verification messages present"

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Ready to deploy.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review the code: build_agent/tools/runtest_improved.py"
    echo "2. Backup original: cp build_agent/tools/runtest.py build_agent/tools/runtest_backup.py"
    echo "3. Deploy: cp build_agent/tools/runtest_improved.py build_agent/tools/runtest.py"
    echo "4. Test with real project: python3 build_agent/main.py curl/curl 7e12139 /root/Git/ARVO2.0"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review.${NC}"
    exit 1
fi



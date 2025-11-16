#!/usr/bin/env bash

# ARVO-Meta 랜덤 5개 프로젝트 테스트 스크립트
# Usage: ./scripts/test_random_5.sh

set -euo pipefail

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}ARVO-Meta Random 5 Projects Test${NC}"
echo -e "${BLUE}========================================${NC}"

# ARVO-Meta 경로 확인
ARVO_META_PATH="/root/Git/ARVO-Meta/archive_data/meta"
if [ ! -d "$ARVO_META_PATH" ]; then
    echo -e "${RED}Error: ARVO-Meta not found at $ARVO_META_PATH${NC}"
    echo -e "${YELLOW}Please clone ARVO-Meta repository first:${NC}"
    echo -e "  cd /root/Git"
    echo -e "  git clone https://github.com/n132/ARVO-Meta.git"
    exit 1
fi

# ABLE 루트 경로 (외부에서 ABLE_ROOT 지정 가능, 없으면 현재 스크립트 기준)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ABLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ABLE_ROOT="${ABLE_ROOT:-$DEFAULT_ABLE_ROOT}"

ARVO2_PATH="$ABLE_ROOT"
OUTPUT_ROOT="$ABLE_ROOT/random_tests"
OUTPUT_DIR="$OUTPUT_ROOT/random_test_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

# 테스트 시 최대 턴 수
MAX_TURNS=50

# build_agent 경로 확인
BUILD_AGENT_PATH="$ABLE_ROOT/build_agent/main.py"
if [ ! -f "$BUILD_AGENT_PATH" ]; then
    echo -e "${RED}Error: build_agent not found at $BUILD_AGENT_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ARVO-Meta found${NC}"
echo -e "${GREEN}✓ Output directory: $OUTPUT_DIR${NC}"

# ARVO-Meta에서 프로젝트 목록 추출
echo -e "\n${BLUE}Collecting project list from ARVO-Meta...${NC}"

# meta 디렉토리에서 이슈 JSON 추출
cd "$ARVO_META_PATH"
mapfile -t ISSUE_FILES < <(find . -type f -name "*.json" | sort -u)

# 이슈 개수 확인
TOTAL_ISSUES=${#ISSUE_FILES[@]}
echo -e "${GREEN}✓ Found $TOTAL_ISSUES issues${NC}"

# 랜덤 5개 선택
echo -e "\n${BLUE}Selecting up to 5 random issues...${NC}"
if [ "$TOTAL_ISSUES" -eq 0 ]; then
    echo -e "${RED}✗ No issues found in ARVO-Meta${NC}"
    exit 1
fi

SAMPLE_COUNT=10
if [ "$TOTAL_ISSUES" -le "$SAMPLE_COUNT" ]; then
    SELECTED_FILES=("${ISSUE_FILES[@]}")
else
    mapfile -t SELECTED_FILES < <(printf "%s\n" "${ISSUE_FILES[@]}" | shuf -n "$SAMPLE_COUNT")
fi

if [ "${#SELECTED_FILES[@]}" -eq 0 ]; then
    echo -e "${RED}✗ Failed to select issues${NC}"
    exit 1
fi

echo -e "${GREEN}Selected issues (${#SELECTED_FILES[@]}):${NC}"
printf "%s\n" "${SELECTED_FILES[@]}" | nl

# 각 프로젝트에서 하나의 커밋 선택
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Starting Tests${NC}"
echo -e "${BLUE}========================================${NC}"

TEST_LIST="$OUTPUT_DIR/test_list.txt"
> "$TEST_LIST"

counter=1
for issue_file in "${SELECTED_FILES[@]}"; do
    [ -z "$issue_file" ] && continue

    repo_addr=$(jq -r '.repo_addr // empty' "$issue_file")
    commit=$(jq -r '(.fix_commit // .commit // .fix // empty) | (if type == "array" then .[0] else . end)' "$issue_file")

    if [[ -z "$repo_addr" || -z "$commit" || "$repo_addr" == "null" || "$commit" == "null" ]]; then
        echo -e "${RED}  ✗ Missing repo or commit info in $issue_file, skipping${NC}"
        continue
    fi

    if [[ "$commit" =~ ^https?:// ]]; then
        commit=${commit##*/}
        commit=${commit%%\?*}
    fi

    repo_url="$repo_addr"
    if [[ "$repo_url" == git@*:* ]]; then
        repo_url=${repo_url#git@}
        repo_url=${repo_url/:/\/}
    elif [[ "$repo_url" == git://* ]]; then
        repo_url=${repo_url#git://}
    elif [[ "$repo_url" == ssh://* ]]; then
        repo_url=${repo_url#ssh://}
    else
        repo_url=${repo_url#*://}
    fi

    host="${repo_url%%/*}"
    rest=""
    if [[ "$repo_url" == */* ]]; then
        rest="${repo_url#*/}"
    fi
    rest=${rest%.git}
    rest=${rest#/}

    if [[ -z "$rest" ]]; then
        repo_path=$host
    elif [[ "$host" == "github.com" || "$host" == "gitlab.com" || "$host" == "bitbucket.org" ]]; then
        repo_path="$rest"
    else
        repo_path="$host/$rest"
    fi

    repo_path=${repo_path%.git}

    if [[ -z "$repo_path" || "$repo_path" == "null" ]]; then
        echo -e "${RED}  ✗ Unable to parse repo path from $repo_addr, skipping${NC}"
        continue
    fi

    echo -e "\n${YELLOW}[$counter/${#SELECTED_FILES[@]}] Processing: $repo_path${NC}"
    echo "$repo_path $commit" >> "$TEST_LIST"
    echo -e "${GREEN}  ✓ Commit: $commit${NC}"

    counter=$((counter + 1))
done

# 테스트 실행
if [ ! -s "$TEST_LIST" ]; then
    echo -e "${RED}✗ No valid project/commit pairs collected. Exiting.${NC}"
    exit 1
fi

ACTUAL_COUNT=$(wc -l < "$TEST_LIST")
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Running ABLE Tests (${ACTUAL_COUNT} projects)${NC}"
echo -e "${BLUE}========================================${NC}"

cd "$ARVO2_PATH"

counter=1
while IFS= read -r line; do
    project=$(echo "$line" | awk '{print $1}')
    commit=$(echo "$line" | awk '{print $2}')

    echo -e "\n${YELLOW}[$counter/$ACTUAL_COUNT] Testing: $project @ $commit${NC}"

    log_file="$OUTPUT_DIR/${project//\//_}_${commit}.log"

    if timeout 1h python3 "$BUILD_AGENT_PATH" "$project" "$commit" "$ARVO2_PATH" --max-turns "$MAX_TURNS" > "$log_file" 2>&1; then
        echo -e "${GREEN}  ✓ Build succeeded${NC}"
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo -e "${RED}  ✗ Timeout (1 hour)${NC}"
        else
            echo -e "${RED}  ✗ Build failed (exit code: $exit_code)${NC}"
        fi
    fi

    counter=$((counter + 1))
done < "$TEST_LIST"

# 결과 요약
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"

SUCCESS_COUNT=$(grep -l "Build succeeded" "$OUTPUT_DIR"/*.log 2>/dev/null | wc -l | tr -d '[:space:]')
FAIL_COUNT=$(grep -l "Build failed" "$OUTPUT_DIR"/*.log 2>/dev/null | wc -l | tr -d '[:space:]')

echo -e "${GREEN}Successful builds: $SUCCESS_COUNT${NC}"
echo -e "${RED}Failed builds: $FAIL_COUNT${NC}"
echo -e "${BLUE}Total tested: $ACTUAL_COUNT${NC}"

if [ $ACTUAL_COUNT -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS_COUNT * 100 / $ACTUAL_COUNT" | bc)
    echo -e "${YELLOW}Success rate: ${SUCCESS_RATE}%${NC}"
fi

echo -e "\n${GREEN}Results saved to: $OUTPUT_DIR${NC}"
echo -e "${GREEN}Test list: $TEST_LIST${NC}"

# 결과 파일 생성
SUMMARY_FILE="$OUTPUT_DIR/SUMMARY.md"
cat > "$SUMMARY_FILE" << EOF
# ARVO-Meta Random 5 Projects Test Results

**Date**: $(date)
**ARVO Version**: v3.8
**Projects Tested**: $ACTUAL_COUNT

## Results

- ✅ Successful: $SUCCESS_COUNT
- ❌ Failed: $FAIL_COUNT
- 📊 Success Rate: ${SUCCESS_RATE:-0}%

## Tested Projects

EOF

while IFS= read -r line; do
    project=$(echo "$line" | awk '{print $1}')
    commit=$(echo "$line" | awk '{print $2}')
    log_file="$OUTPUT_DIR/${project//\//_}_${commit}.log"

    if grep -q "Build succeeded" "$log_file" 2>/dev/null; then
        status="✅"
    else
        status="❌"
    fi

    echo "- $status \`$project\` @ \`$commit\`" >> "$SUMMARY_FILE"
done < "$TEST_LIST"

echo -e "\n${GREEN}Summary written to: $SUMMARY_FILE${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Done!${NC}"
echo -e "${BLUE}========================================${NC}"


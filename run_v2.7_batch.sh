#!/bin/bash
# ARVO2.0 v2.7 Batch Test Script
# Run all 9 projects sequentially

# Don't exit on error - continue with all projects
# set -e

PROJECTS=(
    "ImageMagick/ImageMagick HEAD"
    "harfbuzz/harfbuzz HEAD"
    "bminor/binutils-gdb HEAD"
    "ntop/nDPI HEAD"
    "google/skia HEAD"
    "ArtifexSoftware/Ghostscript.NET HEAD"
    "FFmpeg/FFmpeg HEAD"
    "OpenSC/OpenSC HEAD"
    "OSGeo/gdal HEAD"
)

ROOT_PATH="/root/Git/ARVO2.0/v2.7/"

# Create output directory structure
mkdir -p "${ROOT_PATH}build_agent/output"

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                    ARVO2.0 v2.7 Batch Test                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎯 Changes in v2.7:"
echo "  - Removed && splitting in split_cmd_statements"
echo "  - Bash handles && logic (accurate returncode)"
echo "  - One-Step commands work properly"
echo "  - cd behavior preserved"
echo ""
echo "📊 Testing ${#PROJECTS[@]} projects..."
echo "📁 Output: ${ROOT_PATH}build_agent/output/"
echo "📝 Logs: ${ROOT_PATH}build_agent/log/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

START_TIME=$(date +%s)
SUCCESS_COUNT=0
FAIL_COUNT=0

for project_info in "${PROJECTS[@]}"; do
    IFS=' ' read -r full_name sha <<< "$project_info"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$((SUCCESS_COUNT + FAIL_COUNT + 1))/${#PROJECTS[@]}] $full_name @ $sha"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    PROJECT_START=$(date +%s)
    
    # Run the test
    cd /root/Git/ARVO2.0/build_agent
    python3 main.py "$full_name" "$sha" "$ROOT_PATH"
    EXIT_CODE=$?
    
    PROJECT_END=$(date +%s)
    DURATION=$((PROJECT_END - PROJECT_START))
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ $full_name completed successfully"
        ((SUCCESS_COUNT++))
    else
        echo "❌ $full_name failed with exit code $EXIT_CODE"
        ((FAIL_COUNT++))
    fi
    
    echo "Spend totally $DURATION."
    echo ""
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                        Batch Test Results                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Success: $SUCCESS_COUNT / ${#PROJECTS[@]}"
echo "❌ Failed:  $FAIL_COUNT / ${#PROJECTS[@]}"
echo "⏱️  Total time: ${TOTAL_DURATION}s"
echo ""
echo "📁 Results saved to: ${ROOT_PATH}build_agent/output/"
echo "📝 Logs saved to: ${ROOT_PATH}build_agent/log/"
echo ""

# Generate summary
cat > "${ROOT_PATH}BATCH_RESULTS.txt" << SUMMARY
ARVO2.0 v2.7 Batch Test Results
================================

Date: $(date)
Duration: ${TOTAL_DURATION}s

Success: $SUCCESS_COUNT / ${#PROJECTS[@]}
Failed:  $FAIL_COUNT / ${#PROJECTS[@]}

Projects:
SUMMARY

for project_info in "${PROJECTS[@]}"; do
    IFS=' ' read -r full_name sha <<< "$project_info"
    if [ -f "${ROOT_PATH}build_agent/output/$full_name/track.txt" ]; then
        STATUS=$(grep -q "Congratulations" "${ROOT_PATH}build_agent/output/$full_name/track.txt" 2>/dev/null && echo "✅" || echo "❌")
    else
        STATUS="❌"
    fi
    echo "  $STATUS $full_name @ $sha" >> "${ROOT_PATH}BATCH_RESULTS.txt"
done

echo ""
echo "Summary saved to: ${ROOT_PATH}BATCH_RESULTS.txt"


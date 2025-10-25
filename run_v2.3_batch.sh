#!/bin/bash
# ARVO2.0 v2.3 Batch Test Script
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

ROOT_PATH="/root/Git/ARVO2.0/v2.4/"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 ARVO2.0 v2.3 Batch Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Total projects: ${#PROJECTS[@]}"
echo "Output directory: ${ROOT_PATH}build_agent/"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for i in "${!PROJECTS[@]}"; do
    PROJECT="${PROJECTS[$i]}"
    FULL_NAME=$(echo $PROJECT | awk '{print $1}')
    SHA=$(echo $PROJECT | awk '{print $2}')
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "[$((i+1))/${#PROJECTS[@]}] $FULL_NAME @ $SHA"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    python3 build_agent/main.py "$FULL_NAME" "$SHA" "$ROOT_PATH" || true
    
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️  Warning: $FULL_NAME exited with code $EXIT_CODE"
        echo "Continuing to next project..."
    else
        echo "✅ $FULL_NAME completed successfully"
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Batch test completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Results summary:"
echo "Logs: ${ROOT_PATH}build_agent/log/"
echo "Output: ${ROOT_PATH}build_agent/output/"


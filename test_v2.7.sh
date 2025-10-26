#!/bin/bash
# v2.7 테스트 스크립트

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                     v2.7 테스트 시작                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "프로젝트: bminor/binutils-gdb"
echo "SHA: f02e7de2addf92f02eb7d1e3dfdb18eed4aa6ac9"
echo "시작 시간: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 테스트 실행
python3 main.py \
  bminor/binutils-gdb \
  f02e7de2addf92f02eb7d1e3dfdb18eed4aa6ac9 \
  /root/Git/ARVO2.0/test_results/v2.7

echo ""
echo "종료 시간: $(date '+%Y-%m-%d %H:%M:%S')"

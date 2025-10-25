#!/bin/bash
# ARVO 2.3 Batch 모니터링 스크립트

LOG_DIR="/root/Git/ARVO2.0/v2.3/build_agent/log"
OUTPUT_DIR="/root/Git/ARVO2.0/v2.3/build_agent/output"

echo "🔍 ARVO 2.3 Batch 모니터링 시작..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 배치 스크립트 실행 중인지 확인
while ps aux | grep "run_v2.3_batch.sh" | grep -v grep > /dev/null; do
    clear
    echo "🕐 $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 현재 실행 중인 프로젝트
    CURRENT=$(ps aux | grep "build_agent/main.py" | grep -v grep | awk '{print $NF}' | head -1)
    if [ -n "$CURRENT" ]; then
        echo "▶️  실행 중: $CURRENT"
    else
        echo "⏸️  대기 중..."
    fi
    
    echo ""
    echo "📊 프로젝트별 상태:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    for LOG in $LOG_DIR/*.log; do
        if [ -f "$LOG" ]; then
            PROJECT=$(basename "$LOG" .log | sed 's/_/ /g')
            SIZE=$(wc -l < "$LOG")
            
            # 결과 확인
            if grep -q "Congratulations" "$LOG"; then
                STATUS="✅ 성공"
            elif grep -q "Spend totally" "$LOG"; then
                STATUS="❌ 종료"
            else
                STATUS="🔄 진행중"
            fi
            
            # 턴 수 확인
            TURNS=$(grep -c "ENVIRONMENT REMINDER" "$LOG")
            
            printf "%-40s %8s %s (턴: %d)\n" "$PROJECT" "$STATUS" "$(du -h $LOG | cut -f1)" "$TURNS"
        fi
    done
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💾 디스크 사용량: $(df -h /root/Git/ARVO2.0/v2.3 | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
    echo ""
    
    sleep 10
done

echo ""
echo "🎉 배치 스크립트 완료!"
echo "분석을 시작합니다..."


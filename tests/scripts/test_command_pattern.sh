#!/bin/bash
# Test Command Pattern refactoring

cd /root/Git/ARVO2.0

echo "========================================="
echo "Command Pattern 리팩토링 테스트"
echo "========================================="
echo ""

# Test 1: Original logic (기본값)
echo "🧪 Test 1: Original Logic (Feature Flag OFF)"
echo "  ARVO_USE_COMMAND_PATTERN=false"
echo ""
export ARVO_USE_COMMAND_PATTERN=false
python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0 2>&1 | tee /tmp/test_original.log | tail -20
echo ""
echo "  ✅ Test 1 completed"
echo "  Log: /tmp/test_original.log"
echo ""

# Test 2: Command Pattern (새로운 방식)
echo "🧪 Test 2: Command Pattern (Feature Flag ON)"
echo "  ARVO_USE_COMMAND_PATTERN=true"
echo ""
export ARVO_USE_COMMAND_PATTERN=true
python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0 2>&1 | tee /tmp/test_pattern.log | tail -20
echo ""
echo "  ✅ Test 2 completed"
echo "  Log: /tmp/test_pattern.log"
echo ""

# Compare results
echo "========================================="
echo "📊 비교 결과"
echo "========================================="
echo ""

echo "Turn 수:"
grep -c "### Thought:" /tmp/test_original.log | xargs echo "  Original:"
grep -c "### Thought:" /tmp/test_pattern.log | xargs echo "  Pattern:"
echo ""

echo "성공 여부:"
grep -q "Congratulations" /tmp/test_original.log && echo "  Original: ✅ Success" || echo "  Original: ❌ Failed"
grep -q "Congratulations" /tmp/test_pattern.log && echo "  Pattern: ✅ Success" || echo "  Pattern: ❌ Failed"
echo ""

echo "무한 루프:"
grep -c "ERROR! Your reply does not contain" /tmp/test_original.log | xargs echo "  Original:"
grep -c "ERROR! Your reply does not contain" /tmp/test_pattern.log | xargs echo "  Pattern:"
echo ""

echo "========================================="
echo "✅ 테스트 완료"
echo "========================================="


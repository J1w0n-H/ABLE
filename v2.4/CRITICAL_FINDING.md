# 🚨 치명적 발견: LLM이 MANDATORY를 무시하는 이유

## 문제 현상

**v2.5 binutils-gdb 로그 분석**:

```
Turn N: make -j4 실행
Observation:
  Error 127: makeinfo not found
  🔴🔴🔴 MANDATORY ACTION 🔴🔴🔴
  ⛔ apt-get install texinfo
  DO NOT proceed without executing these!

Turn N+1: 
### Thought:
The root directory contains several important files...
suggests autoconf build system...
run ./configure script...

### Action:
cd /repo && ./configure
```

**LLM이 MANDATORY를 완전히 무시!** ❌

---

## 🔍 가능한 원인 분석

### 가설 1: Observation이 너무 길다

**Observation 구조**:
```
Running `make -j4`...
[수천 줄의 빌드 출력]
Error 127: makeinfo not found
[에러 메시지]
🔴 MANDATORY ACTION
[더 많은 configure 출력]
ENVIRONMENT REMINDER
```

**문제**: 
- MANDATORY 메시지가 **중간**에 위치
- LLM이 전체를 읽지 못하고 **일부만** 읽을 수 있음
- 특히 Thought 생성 시 **시작 부분에 집중**할 가능성

### 가설 2: LLM이 "최신 정보"만 본다

**Observation의 끝 부분**:
```
ENVIRONMENT REMINDER: You have 88 turns left
The container has successfully executed:
cd /repo && apt-get update
cd /repo && apt-get install libgmp-dev
cd /repo && ./configure (4번 반복)
```

**LLM의 추론**:
```
마지막으로 실행한 명령들을 보니 configure를 여러 번...
아, configure를 계속 실행하는 플로우구나?
다음도 configure를 해야겠다!
```

→ **MANDATORY 메시지는 중간에 있어서 놓침!**

### 가설 3: Thought가 Observation 전에 생성됨?

**가능성**:
```
LLM이 Thought를 먼저 생성하고
그 다음에 Observation을 받는 구조?

또는:
Observation이 너무 길어서
Thought 생성 시 일부만 컨텍스트에 포함?
```

---

## 💡 근본 원인

**LLM의 정보 처리 순서**:

```
1. 프롬프트 읽기 (초기에 한 번)
2. Observation 받기 (매 turn)
3. Observation에서 관련 정보 추출
4. Thought 생성
5. Action 결정
```

**문제**:
- MANDATORY 메시지가 Observation의 **중간**에 있음
- LLM이 Observation의 **끝 부분**(ENVIRONMENT REMINDER)에 더 집중
- 프롬프트의 TIER 1 지시는 **초기에 읽은 것**이라 잊혀짐

**결과**:
- LLM이 "configure 반복" 패턴을 **최근 행동**에서 학습
- MANDATORY 메시지를 **중간 노이즈**로 취급
- 프롬프트 지시를 **잊어버림**

---

## 🎯 해결 방안

### Option 1: MANDATORY를 Observation 맨 앞으로 (강력 추천!)

**error_parser.py 수정**:
```python
def extract_critical_errors(output, returncode):
    if returncode == 0:
        return ""
    
    # ... 에러 수집 ...
    
    # v2.5: MANDATORY를 맨 앞에 출력!
    summary = ""
    
    # 1. MANDATORY 먼저!
    if mandatory:
        summary = "\n" + "="*70 + "\n"
        summary += "🔴🔴🔴 MANDATORY ACTION REQUIRED 🔴🔴🔴\n"
        summary += "STOP EVERYTHING AND READ THIS FIRST!\n"
        summary += "="*70 + "\n"
        for s in mandatory:
            summary += f"   ⛔ {s}\n"
        summary += "\nExecute this NOW before reading anything else!\n"
        summary += "="*70 + "\n\n"
    
    # 2. 그 다음 에러 details
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    summary += "🚨 CRITICAL ERRORS DETECTED:\n"
    summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    # ... 에러 라인들 ...
    
    return summary
```

### Option 2: 프롬프트에 "Observation 순서" 명시

```markdown
**HOW TO READ OBSERVATION:**
1. 🔴 FIRST: Look for 🔴 MANDATORY markers (highest priority!)
2. Then: Read error messages
3. Last: Check ENVIRONMENT REMINDER

**CRITICAL:** If you see 🔴 anywhere in Observation:
→ STOP reading
→ Execute the MANDATORY action
→ Do NOT continue to other parts
```

### Option 3: MANDATORY 반복 표시

```python
# Observation의 맨 앞과 맨 뒤에 둘 다 표시
summary_start = "🔴 MANDATORY: apt-get install texinfo (SEE DETAILS BELOW)\n\n"
# ... 중간 내용 ...
summary_end = "\n\n🔴 REMINDER: apt-get install texinfo REQUIRED!\n"
```

---

## 🎓 깨달음

### "위치가 중요하다"

```
중요한 정보의 위치:
❌ Observation 중간 → LLM이 놓침
✅ Observation 맨 앞 → LLM이 먼저 봄
```

### "프롬프트 vs Observation"

```
프롬프트: 초기에 한 번 읽음 → 시간이 지나면 잊혀짐
Observation: 매 turn 받음 → 신선하고 중요

→ 중요한 지시는 Observation에도 포함시켜야!
```

### "최근성 편향 (Recency Bias)"

```
LLM은 Observation의 끝 부분에 더 집중:
- ENVIRONMENT REMINDER: 88 turns left
- Last commands: configure, configure, configure...

→ 패턴 학습: "configure를 계속 실행하는구나"
→ MANDATORY는 중간에 있어서 무시됨
```

---

## 🚀 즉시 적용 가능한 해결책

### 최소 변경, 최대 효과:

**error_parser.py의 출력 순서 변경**:

```python
# Before (현재)
summary = "━━━ ERRORS ━━━\n"
summary += "1. Error...\n"
summary += "2. Error...\n"
summary += "🔴 MANDATORY\n"  ← 중간 또는 끝

# After (개선)
summary = "🔴 MANDATORY: texinfo\n\n"  ← 맨 앞!
summary += "━━━ ERRORS ━━━\n"
summary += "1. Error...\n"
```

**효과**:
- LLM이 Observation을 읽자마자 MANDATORY 발견
- 다른 정보에 방해받지 않음
- 즉시 행동 가능

---

**결론**: 프롬프트가 아무리 좋아도, Observation에서 MANDATORY가 묻히면 소용없다!  
**해결**: MANDATORY를 Observation 맨 앞으로! 🎯


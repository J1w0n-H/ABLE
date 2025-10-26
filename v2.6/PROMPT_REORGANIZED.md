# v2.6: 프롬프트 재구성

## 🎯 목표
LLM이 에러 메시지를 읽고 따르도록 프롬프트 구조 개선

## 📊 현재 문제 (v2.5.2)

### 구조:
```
Line 1-100:   제목, MISSION
Line 101-163: TIERED SYSTEM (TIER 1/2/3)
Line 164-243: WORK PROCESS (1-8단계, MANDATORY!)
Line 244-318: CRITICAL RULES
```

### LLM의 해석:
- WORK PROCESS가 가장 강함 ("⚠️ MANDATORY" × 2)
- TIER 1은 "Error 127 전용"으로 오해
- "READ ERROR MESSAGE"가 TIER 1 안에 숨어있음

## ✅ v2.6: 새 구조

### 우선순위 재배치:
```
1. RULE #1: READ ERROR MESSAGES      (최상단, 무조건 적용)
2. SUGGESTED FIXES                    (⛔ 명령 나오면 복사)
3. TYPICAL WORKFLOW                   (일반 가이드, 조건부)
4. COMMAND FORMAT & TOOLS             (기술 세부사항)
5. CRITICAL RULES                     (형식 규칙)
```

### 핵심 변경:

#### 1. **RULE #1을 최상단으로 (Line 100-142)**
```markdown
╔══════════════════════════════════════════════════════════════════════════╗
║                    🔴 RULE #1: READ ERROR MESSAGES                       ║
╚══════════════════════════════════════════════════════════════════════════╝

**WHEN ANY COMMAND FAILS (returncode != 0):**

1. **READ the error message FIRST**
2. **IF it says "run X"** → Run exactly what it says
3. **DON'T** blindly run configure or make again

**EXAMPLES:**

✅ GOOD: Error says "run make distclean" → Run: make distclean
❌ BAD:  Error says "run make distclean" → Run: ./configure

**🚨 ERROR MESSAGES ARE INSTRUCTIONS!**
```

#### 2. **SUGGESTED FIXES 단순화 (Line 143-162)**
```markdown
**IF YOU SEE ⛔ SUGGESTED COMMANDS IN OBSERVATION:**

⛔ COPY AND RUN THIS EXACT COMMAND:
   apt-get install -y texinfo && make -j4

→ **COPY IT EXACTLY**
→ **RUN IT IN ONE ACTION**
→ **DO NOTHING ELSE**
```

#### 3. **WORK PROCESS → TYPICAL WORKFLOW**
- "MANDATORY" 제거 ❌
- "GENERAL GUIDANCE"로 변경 ✅
- 에러 발생 시 예외 명시 ⚠️

```markdown
## 📋 TYPICAL WORKFLOW (GENERAL GUIDANCE)

**⚠️ IMPORTANT: If ANY command fails, stop and follow RULE #1 above!**
**⚠️ Don't blindly follow this workflow if errors occur!**

1. Explore the project
2. Read build files
3. Identify build system
4. Install dependencies
5. Configure
6. Build
7. Test
```

#### 4. **불필요한 설명 대폭 축소**
- 200+ 줄 → 100줄로 압축
- 중복 제거 (waiting list 설명 3번 → 1번)
- 핵심만 유지

## 📈 효과 예상

### Before (v2.5.2):
```
make 실패 → "WORK PROCESS 6번 보자" → configure 실행
```

### After (v2.6):
```
make 실패 → "RULE #1 보자" → 에러 메시지 읽기 → 메시지대로 실행
```

### LLM 시뮬레이션:
```
읽는 순서:
1. MISSION (Line 96-98)
2. 🔴 RULE #1 (Line 100-142) ← 첫 번째 규칙!
   → "에러 나면 메시지 읽어라!"
   → "configure 재실행 금지!"
3. ⛔ SUGGESTED FIXES (Line 143-162)
   → "⛔ 나오면 복사!"
4. TYPICAL WORKFLOW (Line 165-194)
   → "일반적인 순서"
   → "⚠️ 에러 나면 RULE #1로!"

에러 발생 시:
- "RULE #1: 에러 메시지 읽어라" (최우선)
- "WORKFLOW: 에러 나면 RULE #1로" (복종)
→ ./configure 재실행 방지!
```

## 🔧 구현 파일

- `/root/Git/ARVO2.0/build_agent/agents/configuration.py`
- Line 91-294 전체 재작성

## 📝 다음 단계

1. ✅ 프롬프트 재구성 완료
2. ⏸️ v2.6 테스트 (binutils-gdb)
3. ⏸️ split_cmd_statements 비활성화? (v2.7)

---

**핵심**: LLM이 "RULE #1"을 먼저 읽고 기억하도록 구조 변경!


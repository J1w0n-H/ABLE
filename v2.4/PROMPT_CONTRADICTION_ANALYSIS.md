# 프롬프트 모순 분석 - LLM 입장에서

## 🔴 심각한 문제 발견

LLM이 받는 프롬프트에 **중복되고 모순되는 지시**가 있습니다!

---

## 📍 문제 1: 같은 내용이 2번 나옴

### 위치 1: TIER 1 섹션 (Line 107-129)
```markdown
### 🔴 TIER 1: MANDATORY (shown with ⛔)

You MUST:
3. ⛔ Retry the ORIGINAL failed command that caused Error 127
   - If "make -j4" caused Error 127 → retry "make -j4"
   - DO NOT switch to a different command!
4. ⛔ DO NOT run ./configure repeatedly without making progress

**ANTI-PATTERN:**
❌ make fails → install package → run configure again
✅ make fails → install package → run make again
```

### 위치 2: Error Handling 섹션 (Line 184)
```markdown
8. **Error Handling**:
    - **⚠️ DO NOT re-run ./configure repeatedly** 
    - If make fails, install missing build tools (texinfo, file), NOT re-configure
```

**문제**: 같은 내용이 두 번 나와서 중복됨

---

## 📍 문제 2: 우선순위 혼란

LLM이 읽는 순서:
```
1. TIER 1 섹션 (Line 107)
   "make 실패 → package 설치 → make 재시도"
   
2. WORK PROCESS (Line 147)
   "6. Run build configuration (./configure)"
   "7. Build the project (make -j4)"
   
3. Error Handling (Line 184)
   "DO NOT re-run ./configure repeatedly"
```

**LLM의 혼란**:
- TIER 1에서: "make 실패 → make 재시도"
- WORK PROCESS: "6번 configure, 7번 make" (순서)
- Error Handling: "configure 반복 금지"

**질문**: "make 실패했는데, WORK PROCESS 6번(configure)으로 돌아가야 하나? 아니면 7번(make)을 재시도?"

---

## 📍 문제 3: "ORIGINAL failed command" 불명확

### LLM이 받는 에러 메시지:
```
Running `make -j4`...
makeinfo: not found
Error 127

🔴🔴🔴 MANDATORY ACTION 🔴🔴🔴
   ⛔ apt-get install texinfo

DO NOT proceed without executing these!
```

### LLM의 사고 과정:
```
Q: "ORIGINAL failed command"가 뭐지?
A1: make -j4 (직전에 실행한 것)
A2: makeinfo (에러 메시지에 나온 것)
A3: 전체 빌드 프로세스 (configure부터?)

Q: WORK PROCESS를 보니 configure → make 순서인데...
A: make가 실패했으니 configure부터 다시?

Q: 근데 TIER 1에서 "make fails → make again"이라고 했는데...
A: 혼란스럽다... configure를 실행해볼까?
```

**결과**: LLM이 configure를 선택 ❌

---

## 📍 문제 4: 지시문의 층위 혼재

프롬프트 구조:
```
╔═══ TIER 1 (최상위 우선순위) ═══╗
║ make 실패 → make 재시도         ║
╚═════════════════════════════════╝

WORK PROCESS (절차적 지시):
6. configure 실행
7. make 실행
8. Error Handling (에러 시 대응)

⚠️ CRITICAL RULES (하단 규칙):
- configure 반복 금지
```

**문제**: 최상위(TIER 1), 절차(WORK PROCESS), 규칙(CRITICAL RULES)이 섞여있음

**LLM 입장**:
- "어느 걸 우선해야 하지?"
- "TIER 1이 최상위라고 했지만, WORK PROCESS도 따라야 하고..."
- "CRITICAL RULES도 중요하다는데..."

---

## 💡 근본 원인

### 프롬프트의 구조적 문제

```
[TIER 1: 매우 명확한 지시]
    ↓
[WORK PROCESS: 절차적 단계들]
    ↓ 
[Error Handling: 중복 지시]
    ↓
[CRITICAL RULES: 또 다른 규칙]
```

**LLM이 느끼는 것**:
1. 정보 과부하 (너무 많은 지시)
2. 중복 메시지 (같은 내용이 여러 곳)
3. 우선순위 불명확 (뭘 먼저 따라야?)
4. 문맥 전환 (TIER → PROCESS → RULES)

---

## 🎯 해결 방안

### Option 1: 단순화 (강력 추천)

**TIER 1만 남기고, 나머지 섹션에서 중복 제거**

```markdown
╔══════════════════════════════════════════════════════════════════════════╗
║              💡 ERROR RESPONSE - SIMPLE AND CLEAR                         ║
╚══════════════════════════════════════════════════════════════════════════╝

**IF YOU SEE 🔴 MANDATORY (⛔) IN ANY OBSERVATION:**

1. ⛔ STOP - Execute the suggested apt-get command
2. ⛔ Retry the EXACT same command that just failed
3. ⛔ Example:
   ```
   You ran: make -j4
   Error: makeinfo not found (Error 127)
   Suggestion: ⛔ apt-get install texinfo
   
   YOU MUST DO:
   → apt-get install texinfo
   → make -j4  (retry the SAME command)
   
   DO NOT:
   → ./configure (this is wrong!)
   ```

**SIMPLE RULE:** 
Install package → Retry SAME command → Done ✅

---

**IF YOU SEE 🟡 RECOMMENDED (✅) or 🟢 ADVISORY (💡):**
- Use your judgment
- Usually follow RECOMMENDED
- Consider ADVISORY as hints

---

WORK PROCESS:
[... 기존 내용, 단 Error Handling에서 configure 반복 관련 삭제 ...]
```

### Option 2: 명시적 예시 추가

```markdown
### 🔴 TIER 1 EXAMPLES

**Scenario 1: make fails**
```
Last command: make -j4
Error: makeinfo: not found (Error 127)
Suggestion: ⛔ apt-get install texinfo

✅ CORRECT:
   apt-get install texinfo
   make -j4  ← Retry THIS

❌ WRONG:
   apt-get install texinfo
   ./configure  ← Why configure? make failed, not configure!
```

**Scenario 2: configure fails**
```
Last command: ./configure
Error: aclocal: not found (Error 127)
Suggestion: ⛔ apt-get install automake

✅ CORRECT:
   apt-get install automake
   ./configure  ← Retry THIS

❌ WRONG:
   apt-get install automake
   make  ← Too early! configure didn't finish yet!
```
```

### Option 3: Command History 참조

```markdown
3. ⛔ Retry the ORIGINAL failed command
   
   **HOW TO FIND ORIGINAL FAILED COMMAND:**
   Look at the Observation section:
   - The line before "Running `xxx`..." 
   - The command that shows "executes with returncode: 2"
   - NOT the last successful command
   - NOT the next logical step in WORK PROCESS
   
   **CONCRETE EXAMPLE:**
   ```
   ### Observation:
   Running `make -j4`...  ← THIS is the failed command
   makeinfo: not found
   Error 127
   
   → Retry: make -j4 (NOT ./configure!)
   ```
```

---

## 🎓 LLM 심리 분석

### LLM이 configure를 반복한 이유

**가설 1: WORK PROCESS 순서 집착**
```
WORK PROCESS:
6. configure
7. make
8. Error Handling

→ LLM: "7번에서 에러 → 6번으로 돌아가기?"
```

**가설 2: "재시작" 개념**
```
에러 발생 → "처음부터 다시" → configure가 처음
```

**가설 3: 명확성 부족**
```
"Retry failed command" 
→ LLM: "어떤 명령? makeinfo? make? 전체 빌드?"
→ 확신 없음 → 안전한 선택(configure)
```

---

## ✅ 권장 솔루션

### 최소 변경으로 최대 효과

**1. TIER 1 섹션에 구체적 예시 추가**
```markdown
3. ⛔ Retry the ORIGINAL failed command

**EXAMPLE:**
Observation shows:
   Running `make -j4`...
   Error 127: makeinfo not found
   
Then "ORIGINAL failed command" = make -j4
→ After installing texinfo, run: make -j4
→ DO NOT run: ./configure
```

**2. Error Handling 섹션에서 중복 제거**
```markdown
8. **Error Handling**:
   - Missing headers: Install -dev packages
   - Missing libraries: Install library packages
   - Missing tools: Install build tools
   - **⚠️ Error 127**: Follow TIER 1 instructions at top of prompt
   [삭제: DO NOT re-run ./configure repeatedly]
```

**3. WORK PROCESS에 예외 명시**
```markdown
6-7. configure → make 순서로 실행

**EXCEPTION**: If step 7 (make) fails with Error 127:
→ Install package
→ Retry step 7 (make)
→ DO NOT go back to step 6 (configure)
```

---

## 🎯 결론

**현재 프롬프트의 문제**:
1. ❌ 중복된 지시 (TIER 1 + Error Handling)
2. ❌ 층위 혼재 (최상위 + 절차 + 규칙)
3. ❌ 불명확한 예시 ("ORIGINAL command"가 뭔지)
4. ❌ WORK PROCESS와 충돌 (순서대로 vs 에러 대응)

**LLM이 제대로 수행하려면**:
- ✅ 중복 제거
- ✅ 명확한 예시 (Observation → 어떤 명령)
- ✅ 우선순위 명시 (TIER 1 > WORK PROCESS)
- ✅ 단순한 규칙 (Install → Retry SAME → Done)

---

**평가**: 현재 프롬프트는 **명확해 보이지만, LLM 입장에서는 혼란스럽다!** 🚨


# LLM 시뮬레이션: 왜 configure를 반복하는가?

## 🧠 LLM으로서 프롬프트 읽기

### Phase 1: 초기 학습 (Turn 1)

```
읽는 순서:
1. 제목 (Line 92-94)
2. YOUR MISSION (Line 96-99)
3. 🔴 TIER 1: MANDATORY (Line 107-149)
   - Error 127 → apt-get install
   - DON'T run configure
   - 🚨 READ ERROR MESSAGE ← 중요!
4. 🟡 TIER 2, 🟢 TIER 3 (Line 151-163)
5. WORK PROCESS (Line 167-243)
   - 6. ⚠️ MANDATORY: ./configure
   - 7. ⚠️ MANDATORY: make -j4
   - 8. Error Handling
6. CRITICAL RULES (Line 281-318)
```

**LLM이 학습한 내용:**
```
✅ 기본 흐름: configure → make → runtest
✅ MANDATORY (2회 강조!)
✅ Error 127 → One-Step command
⚠️ "READ ERROR MESSAGE" (1회 언급, TIER 1 안에)
```

---

## 💥 에러 발생 시점 (Turn 7)

### Observation 받음:
```
make -j4 실패
🚨 CRITICAL ERRORS:
1. configure: error: YACC has changed
4. configure: error: run `make distclean` and/or `rm ./config.cache`
make: *** Error 2
```

### LLM의 사고 과정:

```python
# Step 1: 에러 인식
"make가 실패했다"
"returncode: 2"

# Step 2: 분류
"Error 127인가?" → NO
"TIER 1 적용?" → NO (Error 127 아님)

# Step 3: WORK PROCESS 검색
"make는 7번이지"
"실패했으니까..."
"6번 configure로 돌아가야 하나?"

# Step 4: Line 203 참조
"6. ⚠️ MANDATORY: Run build configuration"
"You MUST run `cd /repo && ./configure`"

# Step 5: 결정!
Thought: "configure 실행해야지"
Action: ./configure
```

---

## 🔍 왜 Line 146-149를 무시했나?

### Line 146의 경고:
```
🚨 CRITICAL: READ THE ERROR MESSAGE!
- Error messages contain solution
- ALWAYS read "configure: error:"
- Don't blindly follow WORK PROCESS
```

### LLM이 무시한 이유:

#### 1. **거리 문제 (Recency Bias)**
```
Line 146: TIER 1 안에 있음 (위쪽)
Line 203: WORK PROCESS 6번 (방금 읽음)
```
→ 최근 읽은 WORK PROCESS가 더 강하게 작용

#### 2. **맥락 오해 (Context Misunderstanding)**
```
LLM 해석:
- TIER 1 = "Error 127 전용"
- Line 146 = "TIER 1 내부" → "Error 127일 때만"
- 지금 = "Error 2" → TIER 1 해당 안 됨
```

#### 3. **강도 비교 (Emphasis Comparison)**
```
TIER 1:
- "🚨 CRITICAL" × 1
- "READ ERROR MESSAGE" × 1
- 조건부 ("Error 127", "Missing Headers")

WORK PROCESS:
- "⚠️ MANDATORY" × 2
- "DO NOT SKIP" × 2
- "You MUST" × 2
- 절대적 (무조건)
```
→ WORK PROCESS가 6배 더 강조됨!

#### 4. **절차적 사고 (Procedural Thinking)**
```
LLM:
"6 → 7 → runtest가 순서"
"7번 실패 → 6번으로 돌아가기"
"루프: 6 ⇄ 7"
```

---

## 📊 프롬프트 구조 분석

### 현재 구조:
```
[TIER 1: 특정 에러 처리] (Line 107-149)
  ├─ Error 127
  ├─ Missing Headers
  └─ 🚨 READ ERROR MESSAGE ← 여기 숨어있음!

[WORK PROCESS: 일반 절차] (Line 167-243)
  ├─ 1-5. 준비
  ├─ 6. ⚠️ MANDATORY configure ← 강조!
  ├─ 7. ⚠️ MANDATORY make      ← 강조!
  └─ 8. Error Handling
```

### LLM의 해석:
```
규칙 우선순위:
1. WORK PROCESS (항상 적용)
2. TIER 1 (특정 상황만)

에러 시:
- Error 127? → TIER 1
- 그 외? → WORK PROCESS
```

---

## 🎯 근본 원인

### 프롬프트 설계 실패:

1. **"READ ERROR MESSAGE"의 위치 실패**
   - TIER 1 내부에 있음
   - LLM이 "Error 127 전용"으로 오해
   - 모든 에러에 적용되어야 하는데!

2. **WORK PROCESS의 과도한 강조**
   - "⚠️ MANDATORY" × 2
   - "DO NOT SKIP" × 2
   - LLM이 이걸 최우선으로 인식

3. **구조적 모순**
   ```
   TIER 1 says: "Don't blindly follow WORK PROCESS"
   WORK PROCESS says: "⚠️ MANDATORY!"
   
   LLM thinks: "WORK PROCESS가 MANDATORY인데?"
   ```

4. **경고의 약함**
   ```
   🚨 CRITICAL (1회, TIER 1 안)
   vs
   ⚠️ MANDATORY (2회, WORK PROCESS)
   
   → MANDATORY가 이김!
   ```

---

## ✅ 해결책

### Option A: "READ ERROR MESSAGE"를 최상단으로
```diff
╔══════════════════════════════════════════════════════════════════════════╗
║                C/C++ BUILD ENVIRONMENT CONFIGURATION                     ║
╚══════════════════════════════════════════════════════════════════════════╝

+🔴🔴🔴 RULE #1: READ THE ERROR MESSAGE! 🔴🔴🔴
+
+When ANY command fails:
+1. READ the error message FIRST
+2. If it says "run X", then RUN X
+3. DON'T blindly run configure or make
+4. The error message IS your instruction!
+
+Example:
+Error: "run make distclean" → Run: make distclean
+NOT: ./configure ❌

## 🎯 YOUR MISSION
...
```

### Option B: WORK PROCESS 약화
```diff
-6. ⚠️ MANDATORY: Run build configuration (DO NOT SKIP!)
+6. Run build configuration (usually needed):
    - If configure exists: Run `cd /repo && ./configure`
+   - ⚠️ But if the previous step had errors, READ THE ERROR MESSAGE FIRST!

-7. ⚠️ MANDATORY: Build the project (DO NOT SKIP!)
+7. Build the project:
    - Run `make -j4`
+   - If it fails, DON'T re-run configure unless the error says so!
```

### Option C: 에러 시 프롬프트 오버라이드
```python
# sandbox.py - extract_critical_errors()
if 'configure: error:' in error_text:
    summary += "\n" + "="*70 + "\n"
    summary += "⛔⛔⛔ STOP! READ THIS ERROR MESSAGE! ⛔⛔⛔\n"
    summary += "The error above tells you EXACTLY what to do!\n"
    summary += "DO NOT run ./configure again!\n"
    summary += "="*70 + "\n"
```

### Option D: split_cmd_statements 비활성화 (v2.6)
```python
# Line 422
for ic in init_commands:
    # commands.extend(split_cmd_statements(ic))  # ❌
    commands.append(ic)  # ✅ Bash가 && 처리
```
→ One-Step 명령이 진짜 한 번에 실행됨!

---

## 💡 교훈

### LLM의 행동 패턴:
1. **최근성 우선** (Recency > Distance)
2. **강조도 우선** (MANDATORY > CRITICAL)
3. **절차적 사고** (순서 > 상황)
4. **맥락 오해** (TIER 1 = Error 127 only)

### 프롬프트 설계 원칙:
1. **최우선 규칙은 최상단**
2. **조건 없이 명확히**
3. **과도한 강조 금지** (모순 발생)
4. **에러 시 오버라이드**

### 궁극의 해결책:
**LLM에게 판단 맡기지 말기!**
- split 비활성화
- Bash가 && 처리
- LLM은 명령만 작성


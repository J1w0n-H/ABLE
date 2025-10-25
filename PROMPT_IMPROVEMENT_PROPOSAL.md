# 프롬프트 개선 제안

## 📋 Executive Summary

**문제**: LLM이 make 실패 시 configure.ac를 반복적으로 읽으며 무한 루프에 빠짐
**원인**: 프롬프트 구조의 세 가지 결함
**해결**: 우선순위 재배치 + 조건부 명확화 + 상충 지시 제거

---

## 🚨 현재 프롬프트의 문제점

### Problem 1: 상충하는 지시 (순서 문제)

**현재 구조**:
```
WORK PROCESS:
2. Check configuration files (configure.ac 읽기)  ← 먼저 나옴
4. Analyze build dependencies (AC_CHECK_LIB 찾기)  ← 먼저 나옴
...
8. Error Handling (파일 읽지 마라)  ← 나중에 나옴
```

**LLM 행동**:
```
make 실패 → "무엇을 해야 하나?" → WORK PROCESS 참조
→ Step 2: configure.ac 읽기 ← 이걸 따름
→ Step 4: AC_CHECK_LIB 찾기 ← 이것도 따름
→ (Step 8은 무시됨)
```

### Problem 2: Error Handling이 맨 마지막

**현재**:
```
1-7: 정상 작업
8. Error Handling ← 우선순위 낮음
```

**문제**:
- LLM은 순차적으로 읽음
- "Step 8"이라는 번호가 낮은 우선순위를 암시
- make 실패 → Step 1로 돌아가는 패턴

### Problem 3: 조건부 로직 불명확

**현재**:
```
8. Error Handling: After attempting to build or test...
```

**문제**:
- "After attempting to build"가 언제인지 불명확
- 에러 발생 시 어떤 우선순위로 행동해야 하는지 명시되지 않음

---

## ✅ 해결 방안

### Solution 1: 최우선 규칙을 맨 앞에

```markdown
## ⚡ CRITICAL: ERROR RESPONSE PROTOCOL (HIGHEST PRIORITY)

**IF YOU SEE "💡 SUGGESTED FIXES" IN ANY OBSERVATION:**

### IMMEDIATE ACTIONS (Do this FIRST, before anything else):
1. ⛔ STOP all other planned actions
2. ✅ READ the suggested fixes carefully
3. ✅ EXECUTE each apt-get install command exactly as shown
4. ⛔ DO NOT read configure.ac, Makefile.in, README, or any config files
5. ⛔ DO NOT re-run ./configure (unless specifically suggested)
6. ⛔ DO NOT analyze dependencies manually
7. ✅ After installing all packages, retry the failed command (make, ./configure, etc.)

### Example:
```
Observation shows:
💡 SUGGESTED FIXES:
   • Install file: apt-get install file
   • Install texinfo: apt-get install texinfo

Your IMMEDIATE next action MUST be:
```bash
apt-get install file texinfo
```

DO NOT do any analysis. DO NOT read any files. Install first, retry second.
```

**This protocol overrides ALL other instructions when "💡 SUGGESTED FIXES" appears.**

---

## 📋 NORMAL WORKFLOW (Only when NO errors)

1. Check structure (ls /repo)
2. Try minimal build first
3. Handle errors (see above)
4. Only if no suggested fixes → analyze config files
```

### Solution 2: WORK PROCESS 재구성

```markdown
## 🔄 BUILD WORKFLOW

### Phase 1: Quick Start (Turns 1-3)
1. **Check structure**: `ls -la /repo` (identify build system)
2. **Attempt build immediately**:
   - If configure exists: `cd /repo && ./configure && make -j4`
   - If CMakeLists.txt: `mkdir build && cd build && cmake .. && make -j4`
3. **IF BUILD FAILS** → Go to ERROR PROTOCOL ⚡ (see above)

### Phase 2: Dependency Analysis (ONLY if no 💡 suggestions)
4. **IF no suggested fixes provided**, THEN analyze:
   - Check README for dependency lists
   - Use grep (NOT cat) on configure.ac: `grep "AC_CHECK_LIB" configure.ac`
   - Check error messages for missing .h files
5. **Install identified packages**
6. **Retry build**

### Phase 3: Advanced Troubleshooting (ONLY if still failing)
7. **IF still failing after installing suggested packages**:
   - Read relevant sections of config files (use sed for specific lines)
   - Check environment variables
   - Try single-threaded build: `make` (without -j4)
```

### Solution 3: 명확한 금지 사항

```markdown
## 🚫 FORBIDDEN ACTIONS AFTER BUILD FAILURE

When make/configure fails, DO NOT:
❌ Read entire configure.ac (3907 lines)
❌ Read entire Makefile.in
❌ Re-run ./configure repeatedly
❌ Analyze AC_CHECK_LIB patterns
❌ Search for PKG_CHECK_MODULES

Instead, DO THIS:
✅ Look for "💡 SUGGESTED FIXES" in the error output
✅ Install suggested packages
✅ Retry the failed command
```

---

## 📝 개선된 전체 프롬프트 구조

```markdown
╔══════════════════════════════════════════════════════════════════════════╗
║                C/C++ BUILD ENVIRONMENT CONFIGURATION                     ║
╚══════════════════════════════════════════════════════════════════════════╝

## 🎯 YOUR MISSION
Configure and build a C/C++ project in Docker.
SUCCESS = Build completes + runtest passes with "Congratulations!"

╔══════════════════════════════════════════════════════════════════════════╗
║          ⚡ CRITICAL: ERROR RESPONSE PROTOCOL (TOP PRIORITY)            ║
╚══════════════════════════════════════════════════════════════════════════╝

**IF YOU SEE "💡 SUGGESTED FIXES" IN ANY ERROR OUTPUT:**

1. ⛔ STOP all planned actions immediately
2. ✅ Execute ONLY the suggested apt-get install commands
3. ⛔ DO NOT read configure.ac, Makefile, README, or config files
4. ⛔ DO NOT analyze dependencies or search for AC_CHECK_LIB
5. ⛔ DO NOT re-run ./configure
6. ✅ After installation, retry the exact command that failed

**Example Response:**
```
### Thought:
The error shows 💡 SUGGESTED FIXES. I must install those packages immediately.

### Action:
```bash
apt-get install file texinfo zlib1g-dev
```

**This protocol OVERRIDES all other instructions below.**

---

╔══════════════════════════════════════════════════════════════════════════╗
║                     🔄 NORMAL BUILD WORKFLOW                             ║
║                 (Only follow when NO errors occurred)                    ║
╚══════════════════════════════════════════════════════════════════════════╝

### Phase 1: Quick Start (Turns 1-3)

1. **Check structure**
   ```bash
   ls -la /repo
   ```
   Identify: Makefile? CMakeLists.txt? configure? configure.ac?

2. **Try build IMMEDIATELY** (don't analyze first)
   - Autoconf: `cd /repo && ./configure && make -j4`
   - CMake: `mkdir -p /repo/build && cd /repo/build && cmake .. && make -j4`
   
3. **If build fails** → Check for "💡 SUGGESTED FIXES" → Execute them

### Phase 2: Minimal Analysis (ONLY if no suggestions)

4. **IF error occurred BUT no 💡 suggestions**, THEN:
   - Check error message for specific missing files (.h files)
   - Check README: `grep -i "depend\|require\|install" /repo/README`
   - Use grep (NOT cat): `grep "AC_CHECK_LIB" /repo/configure.ac`

5. **Install identified packages**
   ```bash
   apt-get install lib<name>-dev
   ```

6. **Retry build**

### Phase 3: Advanced (ONLY if still failing)

7. **IF still failing after Phase 2**:
   - Try single-thread: `make` (no -j4)
   - Check specific config sections: `sed -n '100,150p' configure.ac`
   - Set environment variables: `export CC=gcc`

---

╔══════════════════════════════════════════════════════════════════════════╗
║                    🚫 FORBIDDEN ACTIONS                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

**After ANY build failure, NEVER:**
❌ `cat /repo/configure.ac` (3907 lines, wastes tokens)
❌ `cat /repo/Makefile.in` (large file, wastes tokens)
❌ Repeatedly run `./configure` without changing anything
❌ Search for AC_CHECK_LIB / PKG_CHECK_MODULES manually
❌ Analyze config files before checking 💡 SUGGESTED FIXES

**Always CHECK for "💡 SUGGESTED FIXES" FIRST!**

---

╔══════════════════════════════════════════════════════════════════════════╗
║                    ⚠️  CRITICAL RULES                                    ║
╚══════════════════════════════════════════════════════════════════════════╝

### Rule 1: 💡 SUGGESTED FIXES = HIGHEST PRIORITY
If you see "💡 SUGGESTED FIXES", STOP and execute them IMMEDIATELY.
Do NOT read files, analyze, or explore. Just install and retry.

### Rule 2: Try Build FIRST, Analyze SECOND
❌ WRONG: analyze → install deps → build
✅ RIGHT: try build → check errors → install suggested fixes → retry

### Rule 3: configure.ac is for REFERENCE ONLY
- Read it ONLY if no other information available
- Use grep, NOT cat
- NEVER read it after build failures (check 💡 fixes instead)

### Rule 4: One-line Commands
Use `&&` to chain: `cd /repo && ./configure && make -j4`

### Rule 5: DO NOT MODIFY TEST FILES
Fix actual code or install dependencies, never edit test_*.c files

---

## 📖 File Reading Guidelines

| Situation | Command | When |
|-----------|---------|------|
| Build failed | Check "💡 SUGGESTED FIXES" | FIRST |
| No suggestions | `grep "pattern" file` | If needed |
| Small file (<200 lines) | `cat file` | Rarely |
| Large file | `sed -n '100,150p' file` | Very rarely |
| configure.ac | `grep "AC_CHECK_LIB"` | Last resort |

**NEVER `cat configure.ac` or `cat Makefile.in` after build failures!**

---

## 🛠️ Error Response Examples

### ✅ CORRECT Response:
```
Observation:
make: *** Error 2
💡 SUGGESTED FIXES:
   • Install file: apt-get install file
   • Install texinfo: apt-get install texinfo

### Thought:
I see 💡 SUGGESTED FIXES. I must install these packages immediately.

### Action:
```bash
apt-get install file texinfo
```

### ❌ WRONG Response:
```
Observation:
make: *** Error 2
💡 SUGGESTED FIXES:
   • Install file: apt-get install file

### Thought:
I need to understand the build system better. ← WRONG!

### Action:
```bash
cat /repo/configure.ac  ← WRONG! Ignoring suggestions!
```

---

## 📦 Package Management

- Use `apt-get install <packages>` directly
- OR use waiting list: `waitinglist add -p pkg -t apt` then `download`
- After download completes, waiting list becomes EMPTY
- DO NOT call download if list is empty

---

## ✨ Summary: What to Do When Build Fails

1. **Look for "💡 SUGGESTED FIXES"** ← FIRST
2. **If found**: Install packages → Retry build
3. **If NOT found**: Check error message → grep config files → Install → Retry
4. **Never**: Read entire configure.ac or Makefile.in

**The "💡 SUGGESTED FIXES" is your best friend. Trust it!**
```

---

## 🔧 구현 방법

### Option 1: 전면 교체
`configuration.py`의 `init_prompt` 전체를 위 구조로 교체

### Option 2: 단계적 개선
1. ERROR PROTOCOL을 최상단에 추가
2. WORK PROCESS 순서 변경
3. FORBIDDEN ACTIONS 추가

### Option 3: 하이브리드
- 기존 내용 유지
- ERROR PROTOCOL만 최상단에 강조 추가

---

## 📊 예상 효과

### Before:
```
make 실패 (90턴)
→ configure.ac 읽기 (89턴) ← 잘못된 행동
→ AC_CHECK_LIB 검색 (88턴) ← 시간 낭비
→ 또 configure (87턴) ← 무한 루프
...
→ 실패
```

### After:
```
make 실패 (90턴)
→ 💡 SUGGESTED FIXES 확인 (89턴) ← 올바른 행동
→ apt-get install file texinfo (88턴) ← 즉시 해결
→ make 재시도 (87턴) ← 성공!
```

**예상 개선**:
- 빌드 성공률: +40~60%
- 평균 턴 수: -30~50%
- 토큰 사용량: -60~70%

---

## 🎯 권장 사항

**즉시 적용**: Option 1 (전면 교체)

**이유**:
1. 현재 프롬프트는 구조적 결함이 있음
2. 부분 수정으로는 상충 문제 해결 불가
3. 명확한 우선순위 구조 필요

**적용 파일**:
- `/root/Git/ARVO2.0/build_agent/agents/configuration.py`
- `init_prompt` 변수 (line 91~250)

---

**작성일**: 2025-10-24
**작성자**: Analysis by AI Assistant
**버전**: 1.0


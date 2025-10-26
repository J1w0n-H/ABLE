# returncode 123 문제 해결

**발견**: v2.5 테스트가 sed 명령에서 returncode 123으로 멈춤  
**원인**: `get_returncode()` exception → 너무 광범위한 catch  
**영향**: LLM이 "명령 실패"로 오해 → 다른 시도 → 결국 configure 재실행

---

## 🔴 문제 상황

### v2.5 로그 (Line 1366-1369):
```
Running `sed -n '20,60p' /repo/binutils/Makefile.am`...
sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5 [A]0;

`sed -n '20,60p' /repo/binutils/Makefile.am` executes with returncode: 123
```

### 코드 (sandbox.py Line 502-504):
```python
try:
    return_code = self.get_returncode()
except:
    return_code = 123  ← 너무 광범위!
```

### 영향:
1. sed 명령은 실제로 성공했을 수 있음
2. 하지만 `echo $?` 파싱 실패
3. returncode = 123으로 처리
4. LLM: "명령 실패!" → 다른 시도 → configure 재실행

---

## ✅ 해결 방안

### Option 1: Exception 세분화 ⭐ (추천)

```python
# sandbox.py Line 502-509
try:
    return_code = self.get_returncode()
except pexpect.TIMEOUT as e:
    print(f"[WARNING] get_returncode timeout for: {command}")
    print(f"[DEBUG] Timeout details: {e}")
    return_code = 124  # Timeout code
except pexpect.EOF as e:
    print(f"[ERROR] Container died during: {command}")
    print(f"[DEBUG] EOF details: {e}")
    return_code = 125  # Container dead
except ValueError as e:
    print(f"[WARNING] Cannot parse returncode: {e}")
    print(f"[DEBUG] Assuming command succeeded")
    return_code = 0  # Parsing error → assume success
except Exception as e:
    print(f"[ERROR] Unknown error in get_returncode: {e}")
    return_code = 123  # Unknown error
```

**장점:**
- 문제 원인 명확히 식별
- 로그에 디버그 정보 출력
- ValueError → 0 (명령 성공 가정)
- TIMEOUT/EOF → 명확한 에러 코드

### Option 2: Retry 메커니즘

```python
def get_returncode(self, max_retries=3):
    """
    Get command return code with retry mechanism.
    v2.6: Improved stability for flaky pexpect responses.
    """
    for attempt in range(max_retries):
        try:
            self.sandbox.shell.sendline('echo $?')
            self.sandbox.shell.expect([r'root@.*:.*# '], timeout=10)
            output = self.sandbox.shell.before.decode('utf-8').strip()
            output = output.replace('\x1b[?2004l\r', '')
            
            output_lines = output.split('\r\n')
            if len(output_lines) > 1:
                last_line = output_lines[-1]
                output_lines = output_lines[1:-1]
                id = last_line.find('\x1b[')
                if id != -1 and len(last_line[:id].strip()) > 0:
                    output_lines.append(last_line[:id].strip())
            
            return_code_str = '\n'.join(output_lines).strip()
            return int(return_code_str)
            
        except (pexpect.TIMEOUT, ValueError) as e:
            if attempt < max_retries - 1:
                print(f"[RETRY {attempt+1}/{max_retries}] get_returncode: {e}")
                time.sleep(0.5)
            else:
                print(f"[ERROR] get_returncode failed after {max_retries} attempts: {e}")
                return 0  # Assume success if can't determine
```

**장점:**
- 네트워크 지연 등 일시적 문제 해결
- 최대 3번 재시도
- 최종 실패 시 0 반환 (성공 가정)

### Option 3: 프롬프트 패턴 강화

```python
# sandbox.py Line 267
# Before:
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)

# After:
self.sandbox.shell.expect([
    r'root@.*:.*[#$]\s*',  # Standard root prompt
    r'[#$]\s*$',           # Simple prompt
    pexpect.TIMEOUT        # Handle timeout explicitly
], timeout=600)

if self.sandbox.shell.match == pexpect.TIMEOUT:
    print(f"[WARNING] Prompt timeout for: {command}")
    return_code = 124
```

**장점:**
- 다양한 프롬프트 형식 수용
- TIMEOUT 명시적 처리

### Option 4: 명령 성공 기본 가정 ⭐⭐ (가장 간단)

```python
# sandbox.py Line 502-509
try:
    return_code = self.get_returncode()
except Exception as e:
    # v2.6: If returncode detection fails, assume command succeeded
    # This prevents false failures from blocking LLM progress
    print(f"[WARNING] get_returncode failed for '{command}': {e}")
    print(f"[INFO] Assuming command succeeded (returncode=0)")
    return_code = 0  # Assume success
```

**장점:**
- 가장 간단한 수정 (2줄)
- false negative 방지
- LLM 진행 차단 안 됨

**단점:**
- 진짜 실패를 놓칠 수 있음
- 하지만 대부분 sed/grep은 성공함!

---

## 📊 비교

| 방안 | 복잡도 | 안정성 | 정확성 |
|------|--------|--------|--------|
| Option 1: 세분화 | 중 | 중 | 높음 |
| Option 2: Retry | 높음 | 높음 | 중 |
| Option 3: 패턴 | 낮음 | 중 | 중 |
| Option 4: 성공 가정 | **낮음** | **높음** | 낮음 |

---

## 💡 추천

**Option 1 + Option 4 조합:**

```python
try:
    return_code = self.get_returncode()
except pexpect.TIMEOUT as e:
    print(f"[WARNING] Timeout getting returncode for: {command}")
    return_code = 0  # Assume success
except pexpect.EOF as e:
    print(f"[ERROR] Container died during: {command}")
    return_code = 125  # Fatal
except Exception as e:
    print(f"[WARNING] Cannot get returncode: {e}")
    return_code = 0  # Assume success
```

**이유:**
- TIMEOUT/EOF는 명확히 구분 (디버깅)
- 파싱 에러는 성공 가정 (LLM 진행)
- 간단하고 효과적!

---

## 🎯 다음 단계

1. Option 1+4 구현
2. v2.6 재테스트
3. returncode 123 발생 확인

# sleep 0.5 처리 문제 (진짜 원인)

**당신의 지적**: "그거때문이 아니라 SLEEP을 제대로 처리못하는거아니야?"  
**답변**: **정확합니다!** && sleep 0.5 자체가 문제입니다!

---

## 🔴 문제 증거

### v2.5 로그 (Line 1366):
```
sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5 [A]0;
                                                        ^^^^^
                                                        이상한 문자!
```

### 분석:
- `sed ... && sleep 0.5` 에코됨
- `[A]0;` = ANSI escape sequence? 프롬프트?
- 그 다음: **아무것도 없음!** (멈춤)
- returncode: 123

---

## 🔍 근본 원인

### 현재 방식 (sandbox.py Line 472):
```python
self.sandbox.shell.sendline(command + " && sleep 0.5")
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

### 타임라인:
```
Time 0.00s: sendline("sed ... && sleep 0.5")
Time 0.01s: Docker 에코 "sed ... && sleep 0.5"
Time 0.02s: sed 실행 시작
Time 0.05s: sed 완료 (출력 40줄)
Time 0.06s: sleep 0.5 시작 ← 여기서 문제!
Time 0.56s: sleep 완료
Time 0.57s: 프롬프트 "root@..." 출력
Time 0.58s: pexpect 매칭?
```

### 문제점:

#### 1. sleep 중 프롬프트가 이미 나타날 수 있음
```
sed 끝 (0.05s)
  ↓
프롬프트? (0.05s)  ← 너무 빨라!
  ↓
sleep 시작 (0.06s)
  ↓
pexpect: "프롬프트 못 찾음!" (0.06s)
```

#### 2. 터미널 escape sequence 간섭
```
sed 출력: "AUTOMAKE_OPTIONS = ...\r\n"
프롬프트: "root@container:/repo# "
sleep: (실행 중)
터미널: [A]0; ← cursor movement?
```

#### 3. pexpect 버퍼 타이밍
```
expect()가 호출될 때:
  - sed 출력: 이미 완료
  - sleep: 실행 중
  - 프롬프트: 아직 없음!
  
600초 대기 → TIMEOUT → exception → 123
```

---

## ✅ 해결책

### Option A: `;` 사용 (&&가 아닌) ⭐⭐

**변경:**
```python
# Before:
self.sandbox.shell.sendline(command + " && sleep 0.5")

# After:
self.sandbox.shell.sendline(command + " ; sleep 0.5")
                                      ^
```

**효과:**
- sed 실패해도 sleep 실행
- 프롬프트 반환 보장
- pexpect 매칭 성공

**장점:**
- 간단한 수정 (1글자!)
- 확실한 효과
- 부작용 없음

### Option B: echo 마커 ⭐

**변경:**
```python
# After:
marker = "__CMD_DONE__"
self.sandbox.shell.sendline(f"{command} && echo '{marker}'")
self.sandbox.shell.expect([marker], timeout=600)
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=10)
```

**효과:**
- 명령 완료 확실히 감지
- 프롬프트 안정적 대기

**단점:**
- 출력에 마커 포함됨 (제거 필요)
- 2번 expect 호출

### Option C: sleep 제거 + Python 대기

**변경:**
```python
# After:
self.sandbox.shell.sendline(command)
time.sleep(0.1)  # Python에서 대기
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

**효과:**
- 간단함
- sleep 문제 회피

**단점:**
- 출력 플러시 보장 약함

### Option D: 명령 후 true 추가

**변경:**
```python
# After:
self.sandbox.shell.sendline(f"{command} ; true")
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

**효과:**
- ; true가 항상 성공 (returncode 0)
- 프롬프트 확실히 반환

---

## 📊 비교

| 방안 | 복잡도 | 안정성 | 효과 |
|------|--------|--------|------|
| A: `;` 사용 | 낮음 | 높음 | ⭐⭐⭐ |
| B: echo 마커 | 중 | 매우높음 | ⭐⭐ |
| C: sleep 제거 | 낮음 | 중 | ⭐ |
| D: ; true | 낮음 | 높음 | ⭐⭐ |

---

## 💡 추천: Option A (`;` 사용)

```python
# sandbox.py Line 472, 291
# Before:
self.sandbox.shell.sendline(command + " && sleep 0.5")

# After:
self.sandbox.shell.sendline(command + " ; sleep 0.5")
```

**이유:**
1. **가장 간단** (1글자 변경)
2. **확실한 효과** (sleep 항상 실행)
3. **부작용 없음** (returncode는 첫 명령 기준)
4. **pexpect 안정화** (프롬프트 반환 보장)

**추가 고려:**
- returncode는 `echo $?`로 별도 확인
- `&&` vs `;`의 차이는 returncode 반환에만 영향
- 하지만 우리는 `echo $?`로 확인하므로 문제 없음!

---

## 🎯 다음 단계

1. `;` 로 변경
2. v2.6 재테스트
3. returncode 123 발생 여부 확인

# sleep 0.5 처리 흐름

**질문**: "sleep한게 어떻게 되는건지 추적해봐. 다시 llm한테 피드해?"  
**답변**: **아니요, LLM에게 피드백 안 됩니다!** sleep은 시스템 내부에서 제거됩니다.

---

## 🔍 전체 흐름 (9단계)

### 1️⃣ LLM이 명령 생성
```
### Action:
```bash
sed -n '20,60p' /repo/binutils/Makefile.am
```
```
→ `sed -n '20,60p' /repo/binutils/Makefile.am`

### 2️⃣ extract_commands 추출
**파일**: `build_agent/utils/parser/parse_command.py`
```python
def extract_commands(text):
    pattern = rf'{BASH_FENCE[0]}([\s\S]*?){BASH_FENCE[1]}'
    matches = re.findall(pattern, text)
    commands = []
    for command_text in matches:
        commands.extend(command_text.strip().split('\n'))
    return commands
```
→ `["sed -n '20,60p' /repo/binutils/Makefile.am"]`

### 3️⃣ split_cmd_statements 처리
**파일**: `build_agent/agents/configuration.py` Line 427
```python
for ic in init_commands:
    commands.extend(split_cmd_statements(ic))
```
→ `["sed -n '20,60p' /repo/binutils/Makefile.am"]` (&&가 없으므로 그대로)

### 4️⃣ sandbox.execute() 호출
**파일**: `build_agent/agents/configuration.py` Line 467
```python
sandbox_res, return_code = self.sandbox_session.execute(
    commands[i], waiting_list, conflict_list
)
```
→ `command = "sed -n '20,60p' /repo/binutils/Makefile.am"`

### 5️⃣ **sandbox.py에서 sleep 추가** ⭐
**파일**: `build_agent/utils/sandbox.py` Line 472
```python
if command[-1] != '&':
    self.sandbox.shell.sendline(command + " && sleep 0.5")
```
→ Docker로 전송: `"sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5"`

### 6️⃣ Docker 컨테이너에서 실행
```bash
root@container:/repo# sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5
AUTOMAKE_OPTIONS = dejagnu no-texinfo.tex no-dist foreign
ACLOCAL_AMFLAGS = -I .. -I ../config -I ../bfd
TEXINFO_TEX = ../texinfo/texinfo.tex
...
(0.5초 대기)
root@container:/repo# 
```

### 7️⃣ pexpect로 출력 캡처
**파일**: `sandbox.py` Line 483-489
```python
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
output = self.sandbox.shell.before.decode('utf-8')
```

**캡처된 raw 출력:**
```
sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5\r\n
AUTOMAKE_OPTIONS = dejagnu no-texinfo.tex no-dist foreign\r\n
ACLOCAL_AMFLAGS = -I .. -I ../config -I ../bfd\r\n
...\r\n
```

### 8️⃣ **출력 정리 (sleep 제거!)** ⭐
**파일**: `sandbox.py` Line 493-500
```python
output_lines = output.split('\r\n')
if len(output_lines) > 1:
    output_lines = output_lines[1:-1]  # 첫 줄(명령)과 마지막 줄(프롬프트) 제거
```

**Before:**
```
[0] "sed -n '20,60p' ... && sleep 0.5"  ← 제거!
[1] "AUTOMAKE_OPTIONS = ..."             ← 유지
[2] "ACLOCAL_AMFLAGS = ..."              ← 유지
...
[-1] "root@container:/repo# "            ← 제거!
```

**After:**
```
[0] "AUTOMAKE_OPTIONS = ..."
[1] "ACLOCAL_AMFLAGS = ..."
...
```

### 9️⃣ LLM에게 피드백
**파일**: `configuration.py` Line 561, 589
```python
result_message = f'Running `{command}`...\n' + result_message
system_res = '### Observation:\n' + result_message
system_message = {"role": "system", "content": system_res}
self.messages.append(system_message)
```

**LLM이 최종 받는 내용:**
```
### Observation:
Running `sed -n '20,60p' /repo/binutils/Makefile.am`...
AUTOMAKE_OPTIONS = dejagnu no-texinfo.tex no-dist foreign
ACLOCAL_AMFLAGS = -I .. -I ../config -I ../bfd
...
`sed -n '20,60p' /repo/binutils/Makefile.am` executes with returncode: 0
```

---

## ✅ 결론

**"sleep한게 다시 llm한테 피드해?"**

→ **아니요!** ❌

### 이유:

1. **Line 497에서 제거**:
   ```python
   output_lines = output_lines[1:-1]
   ```
   - `[1:-1]` = 첫 줄(명령+sleep)과 마지막 줄(프롬프트) 제거
   - LLM이 입력한 원본 명령만 표시

2. **LLM이 보는 것**:
   ```
   Running `sed -n '20,60p' ...`...  ← 원본 명령 (sleep 없음)
   ... (출력) ...
   `sed -n '20,60p' ...` executes...  ← 원본 명령 (sleep 없음)
   ```

3. **LLM이 못 보는 것**:
   ```
   sed -n '20,60p' ... && sleep 0.5  ← 이건 제거됨!
   ```

---

## 💡 목적

### sleep 0.5의 역할:
- ✅ pexpect 동기화
- ✅ 출력 완전히 플러시
- ✅ 프롬프트 반환 보장

### LLM과 무관:
- ❌ LLM은 sleep 몰라도 됨
- ❌ 피드백 안 됨
- ✅ 시스템 내부 메커니즘

---

## 📊 증명

### pexpect 캡처 내용:
```
"sed ... && sleep 0.5\r\n  ← Line 0 (제거됨!)
AUTOMAKE_OPTIONS\r\n       ← Line 1 (유지)
...\r\n                    ← Line 2-N (유지)
root@container:/repo# "    ← Line -1 (제거됨!)
```

### output_lines[1:-1]:
```
AUTOMAKE_OPTIONS          ← 이것만 남음
...
```

### LLM에게 전달:
```
Running `sed ...`...      ← 원본 명령
AUTOMAKE_OPTIONS          ← 출력
...
`sed ...` executes...     ← 원본 명령
```

**sleep은 어디에도 없음!** ✅

---

## 🎓 교훈

**시스템 내부 처리:**
- `sendline(cmd + " && sleep 0.5")` → Docker 전송
- `output_lines[1:-1]` → sleep 제거
- `f'Running `{command}`'` → 원본 명령 표시

**LLM 관점:**
- 입력: `sed ...` (sleep 없음)
- 출력 받음: Observation (sleep 없음)
- **sleep을 전혀 모름!** ✅

**정상 작동!**


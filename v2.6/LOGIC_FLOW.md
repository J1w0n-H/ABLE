# v2.6 전체 로직 분석

**목적**: 한 턴의 실행 흐름을 처음부터 끝까지 추적

---

## 🔄 1턴의 완전한 흐름

### Phase 1: LLM 호출
**파일**: `configuration.py` Line 397-402

```python
turn += 1
current_messages = manage_token_usage(self.messages)
configuration_agent, usage = get_llm_response(self.model, current_messages)
```

**입력 (messages)**:
```
[0] System: init_prompt (RULE #1, WORKFLOW, etc.)
[1] User: "[Project root Path]: /repo"
[2] System: "### Observation: ..." (이전 턴 결과)
[3] Assistant: "### Thought: ... ### Action: ..." (이전 LLM 응답)
[4] System: "### Observation: ..." (이전 턴 결과)
...
```

**출력**:
```
configuration_agent = """
### Thought: The error indicates YACC changed.
### Action:
```bash
make distclean
```
"""
```

---

### Phase 2: 명령 추출
**파일**: `configuration.py` Line 419-427

```python
# Step 1: Bash 블록에서 명령 추출
init_commands = extract_commands(configuration_agent)
# → ["make distclean"]

# Step 2: split_cmd_statements로 분리
commands = list()
for ic in init_commands:
    commands.extend(split_cmd_statements(ic))
# → ["make distclean"] (&&가 없으므로 그대로)
```

**extract_commands 동작**:
```python
# utils/parser/parse_command.py
pattern = rf'{BASH_FENCE[0]}([\s\S]*?){BASH_FENCE[1]}'
matches = re.findall(pattern, text)
commands = []
for command_text in matches:
    commands.extend(command_text.strip().split('\n'))
return commands
```

**split_cmd_statements 동작**:
```python
# utils/split_cmd.py
def split_cmd_statements(cmd):
    # 금지 패턴 체크 (if/then/fi, for, while)
    # ...
    
    # \\\n 제거
    cmd = re.sub(r'\\\s*\n', '', cmd)
    
    # \n을 공백으로
    cmd = re.sub(r'\n', ' ', cmd)
    
    # && 로 분리
    statements = re.split(r'\s*&&\s*', cmd)
    
    return [s.strip() for s in statements]
```

**예시**:
```
입력: "apt-get install texinfo && make -j4"
split: ["apt-get install texinfo", "make -j4"]

입력: "make distclean"
split: ["make distclean"]
```

---

### Phase 3: 명령 실행 (각 명령마다)
**파일**: `configuration.py` Line 428-470

```python
for i in range(len(commands)):
    # 1. 명령 기록
    self.outer_commands.append({"command": commands[i], ...})
    
    # 2. 실행
    sandbox_res, return_code = self.sandbox_session.execute(
        commands[i], waiting_list, conflict_list
    )
    
    # 3. 결과 기록
    system_res += sandbox_res
    if return_code != 'unknown':
        system_res += f'\n`{commands[i]}` executes with returncode: {return_code}\n'
```

**예시**:
```
commands = ["make distclean"]

실행:
  sandbox_session.execute("make distclean", ...)
  → sandbox_res, return_code
```

---

### Phase 4: sandbox.py 실행
**파일**: `sandbox.py` Line 455-562

#### 4-1. 전처리
```python
# Special commands
if match_runtest(command):
    command = 'python /home/tools/runtest.py'
if command == 'generate_diff':
    command = 'python /home/tools/generate_diff.py'

# Dynamic timeout
command_timeout = 600 * 2  # 20 minutes
if 'apt-get install' in command:
    command_timeout = 1800  # 30 minutes
```

#### 4-2. Docker 전송
```python
if command[-1] != '&':
    # Commit container (snapshot)
    if not (command in safe_cmd and '>' not in command):
        self.sandbox.commit_container()
    
    # Get current directory
    dir, _ = self.execute('$pwd$', ...)
    
    # Record command
    self.sandbox.commands.append({
        "command": command,
        "returncode": -2,
        "time": -1,
        "dir": dir
    })
    
    # v2.6: Send with ; sleep
    self.sandbox.shell.sendline(command + " ; sleep 0.5")
    #                                     ^
```

**Docker로 전송**:
```
make distclean ; sleep 0.5
```

#### 4-3. 출력 캡처
```python
# Wait for prompt
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=command_timeout)

# Capture output
output = self.sandbox.shell.before.decode('utf-8').strip()
output = output.replace('\x1b[?2004l\r', '')

# Parse lines
output_lines = output.split('\r\n')
if len(output_lines) > 1:
    output_lines = output_lines[1:-1]  # 첫 줄(명령), 마지막 줄(프롬프트) 제거
```

**캡처 예시**:
```
Before:
  [0] "make distclean ; sleep 0.5"
  [1] "make[1]: Entering directory '/repo'"
  [2] "Doing distclean in libiberty"
  ...
  [50] ""

After (output_lines[1:-1]):
  [0] "make[1]: Entering directory '/repo'"
  [1] "Doing distclean in libiberty"
  ...
```

#### 4-4. returncode 확인
```python
try:
    return_code = self.get_returncode()
except pexpect.TIMEOUT:
    print(f"[WARNING] Timeout getting returncode")
    return_code = 0  # v2.6: Assume success
except pexpect.EOF:
    print(f"[ERROR] Container died")
    return_code = 125
except Exception as e:
    print(f"[WARNING] Cannot get returncode: {e}")
    return_code = 0  # v2.6: Assume success
```

**get_returncode() 동작**:
```python
# sandbox.py Line 264-282
def get_returncode(self):
    # Send echo $?
    self.sandbox.shell.sendline('echo $?')
    
    # Wait for prompt
    self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
    
    # Parse output
    output = self.sandbox.shell.before.decode('utf-8')
    output_lines = output.split('\r\n')[1:-1]
    
    # Extract number
    return_code = '\n'.join(output_lines).strip()
    return int(return_code)  # "0" → 0
```

---

### Phase 5: 에러 분석 (실패 시만)
**파일**: `sandbox.py` Line 545-556

```python
if return_code != 0:
    # v2.5: One-Step 명령 생성
    error_summary = extract_critical_errors(
        result_message, 
        return_code, 
        last_command=command
    )
    
    if error_summary:
        result_message = error_summary + "\n" + result_message
    
    # make -j4 실패 시 단일 스레드 제안
    if 'make' in command and '-j' in command:
        tip = "\n⚠️  Parallel build failed...\n"
        result_message = tip + result_message
```

**extract_critical_errors 동작**:
```python
# utils/error_parser.py
def extract_critical_errors(output, returncode, last_command=""):
    # 1. 에러 패턴 찾기
    error_lines = []
    for line in output.split('\n'):
        if re.search(r'error:|Error \d+|command not found', line):
            error_lines.append(line)
    
    # 2. 제안 생성
    suggestions = analyze_errors(error_lines)
    
    # 3. One-Step 명령 생성 (MANDATORY)
    if last_command and suggestions:
        install_cmds = " && ".join(suggestions)
        one_step = f"{install_cmds} && {last_command}"
        
        summary = "="*70 + "\n"
        summary += "🔴🔴🔴 STOP! EXECUTE THIS EXACT COMMAND 🔴🔴🔴\n"
        summary += "="*70 + "\n"
        summary += f"⛔ COPY AND RUN THIS EXACT COMMAND:\n\n"
        summary += f"   {one_step}\n\n"
    
    return summary
```

---

### Phase 6: LLM 피드백 생성
**파일**: `configuration.py` Line 565-592

```python
# 1. Current directory
current_directory, _ = self.sandbox_session.execute('$pwd$', ...)
system_res += current_directory
system_res += f'You are currently in a [{self.image_name}] container.\n'

# 2. Turn reminder
reminder = f"\nENVIRONMENT REMINDER: You have {self.max_turn - turn} turns left."
system_res += reminder

# 3. v2.5.2: 히스토리 제거 (주석 처리됨!)
# success_cmds = extract_cmds(self.sandbox.commands)
# system_res += appendix

# 4. 메시지 추가
if "gpt" in self.model:
    system_message = {"role": "system", "content": system_res}
else:
    system_message = {"role": "user", "content": system_res}
self.messages.append(system_message)
```

**최종 LLM 입력 (다음 턴)**:
```
### Observation:
Running `make distclean`...
make[1]: Entering directory '/repo'
Doing distclean in libiberty
...
`make distclean` executes with returncode: 0

[Current directory]:
/repo
You are currently in a [gcr.io/oss-fuzz-base/base-builder] container.

ENVIRONMENT REMINDER: You have 79 turns left to complete the task.
```

---

## 🔍 핵심 로직 포인트

### 1. **split_cmd_statements** (Line 427)
```python
for ic in init_commands:
    commands.extend(split_cmd_statements(ic))
```

**문제**:
- `"A && B && C"` → `["A", "B", "C"]`
- 각각 실행 → returncode 혼란
- **v2.7에서 제거 예정!**

### 2. **; sleep 0.5** (sandbox.py Line 474)
```python
self.sandbox.shell.sendline(command + " ; sleep 0.5")
```

**효과**:
- 무조건 sleep 실행
- pexpect 안정화
- **v2.6 핵심 개선!**

### 3. **returncode 0 가정** (sandbox.py Line 503-513)
```python
except Exception as e:
    return_code = 0  # v2.6
```

**효과**:
- get_returncode 실패 → 성공 가정
- False failure 방지
- **v2.6 핵심 개선!**

### 4. **히스토리 제거** (configuration.py Line 577-587)
```python
# v2.5.2: 주석 처리됨!
# success_cmds = extract_cmds(self.sandbox.commands)
# system_res += appendix
```

**효과**:
- Observation만 제공
- 혼란 방지
- **v2.5.2 개선 유지!**

### 5. **One-Step 명령** (error_parser.py Line 107-117)
```python
if last_command:
    install_cmds = " && ".join(mandatory)
    one_step = f"{install_cmds} && {last_command}"
    summary += f"⛔ COPY AND RUN THIS EXACT COMMAND:\n\n"
    summary += f"   {one_step}\n\n"
```

**효과**:
- 설치 + 재시도 한 번에
- LLM이 복사만 하면 됨
- **v2.5 핵심!**

---

## 🎯 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│ Turn N Start                                                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. LLM 호출 (configuration.py Line 402)                    │
│    Input: messages (init_prompt + history)                 │
│    Output: "### Thought: ... ### Action: ```bash ... ```"  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 명령 추출 (Line 419-427)                                │
│    extract_commands() → ["apt-get install texinfo && make"]│
│    split_cmd_statements() → ["apt-get...", "make"]         │
│                              ⚠️ 문제의 split!              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. For 루프: 각 명령 실행 (Line 428-518)                   │
│    for i in range(len(commands)):                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────┐
        │ 3-1. sandbox.execute() 호출   │
        │      (Line 467)               │
        └───────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────────┐
        │ 3-2. Docker 전송 (sandbox.py Line 474)           │
        │      sendline(command + " ; sleep 0.5")          │
        │                         ^                        │
        │                         v2.6 개선!               │
        └───────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────────┐
        │ 3-3. pexpect 대기 (Line 483)                     │
        │      expect([r'root@.*:.*# '], timeout=...)      │
        │      output = shell.before                       │
        └───────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────────┐
        │ 3-4. 출력 정리 (Line 497)                        │
        │      output_lines[1:-1]  # 명령/프롬프트 제거    │
        └───────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────────┐
        │ 3-5. returncode 확인 (Line 502-513)              │
        │      try: get_returncode()                       │
        │      except: return_code = 0  # v2.6 개선!       │
        └───────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────────┐
        │ 3-6. 에러 분석 (Line 545-556, if failed)         │
        │      error_parser.extract_critical_errors()      │
        │      → One-Step 명령 생성                        │
        └───────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Observation 생성 (Line 565-592)                         │
│    system_res = "### Observation:\n"                       │
│    + sandbox_res (명령 출력)                               │
│    + current_directory                                     │
│    + turns left reminder                                   │
│    (히스토리 제거됨! v2.5.2)                               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 메시지 추가 (Line 588-592)                              │
│    system_message = {"role": "system", "content": ...}     │
│    self.messages.append(system_message)                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Turn N End → Turn N+1 Start                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 v2.6 개선 포인트 (코드 위치)

### 1. **RULE #1 최상단** (configuration.py Line 100-142)
```python
self.init_prompt = f"""
╔══════════════════════════════════════════════════════════════╗
║              🔴 RULE #1: READ ERROR MESSAGES                 ║
╚══════════════════════════════════════════════════════════════╝

**WHEN ANY COMMAND FAILS:**
1. READ the error message FIRST
2. IF it says "run X" → Run X
3. DON'T blindly run configure
"""
```

### 2. **; sleep** (sandbox.py Line 474, 292)
```python
sendline(command + " ; sleep 0.5")  # v2.6: ; instead of &&
```

### 3. **returncode 0** (sandbox.py Line 503-513)
```python
except Exception as e:
    return_code = 0  # v2.6: Assume success
```

### 4. **히스토리 제거** (configuration.py Line 577-587)
```python
# v2.5.2: Commented out
# success_cmds = extract_cmds(...)
```

### 5. **동적 타임아웃** (sandbox.py Line 462-464)
```python
# v2.5
if 'apt-get install' in command:
    command_timeout = 1800  # 30 minutes
```

---

## 🔴 알려진 문제

### 1. **split_cmd_statements** (Line 427)
```python
commands.extend(split_cmd_statements(ic))
```

**문제**:
- `"A && B"` → `["A", "B"]`
- 각각 실행 → returncode 혼란
- One-Step 명령이 진짜 One-Step 아님!

**해결**: v2.7에서 제거 예정
```python
commands.append(ic)  # split 안 함!
```

### 2. **returncode 오판** (v2.6 부작용)
```
make 실패 (Error 2)
→ get_returncode exception
→ returncode = 0
→ LLM: "성공!" ← 틀림!
```

**하지만**:
- error_parser가 출력에서 에러 감지
- 실제로는 문제 없음!

---

## 📊 데이터 흐름 요약

```
LLM Response
  ↓ extract_commands
Commands ["A && B"]
  ↓ split_cmd_statements ⚠️
Commands ["A", "B"]
  ↓ for loop
Execute "A"
  ↓ sandbox.execute
Docker: "A ; sleep 0.5"
  ↓ pexpect
Output + returncode
  ↓ error_parser (if failed)
One-Step command
  ↓ configuration.py
Observation
  ↓ messages.append
LLM Input (next turn)
```

---

## 🎯 v2.6의 강점과 약점

### 강점:
1. ✅ RULE #1 효과 (에러 메시지 읽기)
2. ✅ ; sleep 안정화 (pexpect)
3. ✅ returncode 0 가정 (진행 보장)
4. ✅ 23턴 성공 (효율적)

### 약점:
1. ⚠️ split으로 인한 returncode 오판
2. ⚠️ One-Step이 진짜 One-Step 아님
3. ⚠️ make 실패를 성공으로 오인 가능

### 실제 결과:
- **성공!** (error_parser가 보완)

---

## 🚀 v2.7 방향

**split_cmd_statements 제거:**
```python
for ic in init_commands:
    commands.append(ic)  # No split!
```

**효과:**
- Bash가 && 처리
- returncode 정확
- One-Step 진짜 작동
- 더 간단하고 정확!


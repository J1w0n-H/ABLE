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


# 🔴 One-Step 실패 근본 원인 발견!

## 문제

### LLM 응답
```bash
apt-get install -y texinfo && make -j4
```

### 실제 실행
```bash
Turn 1: apt-get install -y texinfo
Turn 2: make -j4
```

---

## 🔍 코드 추적

### 1. extract_commands (정상)
```python
# parse_command.py Line 21-28
def extract_commands(text):
    pattern = rf'{BASH_FENCE[0]}([\s\S]*?){BASH_FENCE[1]}'
    matches = re.findall(pattern, text)
    commands = []
    for command_text in matches:
        if command_text:
            commands.extend(list(filter(None, command_text.strip().split('\n'))))
    return commands

# 결과: ['apt-get install -y texinfo && make -j4']  ✅
```

### 2. split_cmd_statements (문제!)
```python
# split_cmd.py Line 65
statements = re.split(r'\s*&&\s*', cmd)

# 결과: ['apt-get install -y texinfo', 'make -j4']  ❌
```

### 3. configuration.py (분리 실행)
```python
# configuration.py Line 419-422
init_commands = extract_commands(configuration_agent)
commands = list()
for ic in init_commands:
    commands.extend(split_cmd_statements(ic))  # ← 여기서 분리!

# Line 428
for i in range(len(commands)):
    sandbox_res, return_code = self.sandbox_session.execute(commands[i], ...)
```

---

## 💡 근본 원인

**`split_cmd_statements`의 설계 목적**:
```python
# 원래 용도: waitinglist add를 여러 개 연결한 경우
cmd = """waitinglist add -p pkg1 -t apt && 
waitinglist add -p pkg2 -t apt &&
waitinglist add -p pkg3 -t apt"""

# split_cmd_statements로 분리
# → ['waitinglist add -p pkg1 -t apt',
#     'waitinglist add -p pkg2 -t apt', 
#     'waitinglist add -p pkg3 -t apt']
```

**부작용**: 모든 `&&` 명령이 분리됨!
```python
# One-Step도 분리됨
cmd = "apt-get install -y texinfo && make -j4"
# → ['apt-get install -y texinfo', 'make -j4']  ❌
```

---

## 🎯 해결 방안

### Option 1: split_cmd_statements 비활성화 (간단)
```python
# configuration.py Line 419-422
init_commands = extract_commands(configuration_agent)
commands = list()
for ic in init_commands:
    # ❌ commands.extend(split_cmd_statements(ic))
    commands.append(ic)  # ✅ 분리하지 않고 그대로 사용
```

**장점**: 즉시 해결  
**단점**: waitinglist add 여러 개 연결 못함

### Option 2: 조건부 분리 (안전)
```python
# configuration.py
for ic in init_commands:
    # One-Step 명령은 분리하지 않음
    if 'apt-get install' in ic and '&& make' in ic:
        commands.append(ic)  # 그대로 유지
    elif 'apt-get install' in ic and '&& ./configure' in ic:
        commands.append(ic)  # 그대로 유지
    else:
        commands.extend(split_cmd_statements(ic))  # 기존 로직
```

**장점**: waitinglist와 One-Step 모두 지원  
**단점**: 조건이 복잡함

### Option 3: 특별한 마커 사용
```python
# error_parser.py
# ONE_STEP 명령에 특별한 마커 추가
one_step_command = f"__ONESTEP__{install_cmds} && {last_command}"

# configuration.py
for ic in init_commands:
    if ic.startswith('__ONESTEP__'):
        ic = ic.replace('__ONESTEP__', '')
        commands.append(ic)  # 분리하지 않음
    else:
        commands.extend(split_cmd_statements(ic))
```

**장점**: 명확한 구분  
**단점**: 마커 추가 필요

### Option 4: TIER 1 전용 처리 (권장!)
```python
# configuration.py Line 419-422
init_commands = extract_commands(configuration_agent)
commands = list()
for ic in init_commands:
    # TIER 1 명령 감지: apt-get install과 빌드 명령의 조합
    if re.match(r'apt-get install.*&&.*(make|configure|cmake)', ic):
        # One-Step Fix Command - 분리하지 않음!
        commands.append(ic)
    else:
        # 기존 로직: waitinglist 등을 위해 분리
        commands.extend(split_cmd_statements(ic))
```

**장점**: 
- 최소 변경
- One-Step과 기존 기능 모두 유지
- 명확한 의도

---

## 📊 영향 분석

### 현재 (v2.5)
```
LLM: apt-get install -y texinfo && make -j4
→ split_cmd_statements
→ ['apt-get install -y texinfo', 'make -j4']
→ 순차 실행 (2개 턴 소모)
→ configure 반복 가능성
```

### 수정 후 (v2.5.2)
```
LLM: apt-get install -y texinfo && make -j4
→ One-Step 감지
→ ['apt-get install -y texinfo && make -j4']
→ 단일 실행 (1개 턴)
→ 원자성 보장!
```

---

## 🚨 충격적인 발견

**One-Step 시스템은 처음부터 작동하지 않았음!**

- error_parser.py: One-Step 명령 생성 ✅
- sandbox.py: last_command 전달 ✅
- configuration.py 프롬프트: One-Step 설명 ✅
- **configuration.py Line 422: 명령 분리** ❌❌❌

**v2.5에서 FFmpeg이 성공한 이유**:
- FFmpeg은 Error 127이 적게 발생
- 다른 이유로 성공했을 가능성

---

## ⚡ 즉시 수정 필요

**v2.5.2로 즉시 업그레이드 필요!**

```python
# configuration.py Line 419-422
init_commands = extract_commands(configuration_agent)  
commands = list()
for ic in init_commands:
    # 🆕 v2.5.2: ONE-STEP FIX COMMAND DETECTION
    # apt-get install과 빌드/configure 명령의 조합은 분리하지 않음
    if re.match(r'apt-get install.*&&.*(make|configure|cmake|bazel)', ic):
        commands.append(ic)  # Keep atomic!
    else:
        commands.extend(split_cmd_statements(ic))  # Split for waitinglist

# 추정 효과
- binutils-gdb: 100턴 → 20턴 성공
- OpenSC: bootstrap 반복 해결
- 모든 Error 127 케이스 개선
```

---

## 🎯 결론

**v2.5는 반쪽짜리 구현이었음!**

- 코드: One-Step 명령 생성 ✅
- 프롬프트: One-Step 설명 ✅
- **실행**: 명령 분리로 무효화** ❌

**해결**: Line 422 수정으로 즉시 해결 가능!


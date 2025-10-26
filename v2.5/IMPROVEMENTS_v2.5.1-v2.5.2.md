# ARVO v2.5.1 개선사항

## 문제 분석 결과

### 답지 빌드 (수동 테스트)
```bash
1. apt-get update -qq
2. apt-get install -y libgmp-dev libmpfr-dev
3. ./configure
4. make -j4 → Error 127: makeinfo not found
5. apt-get install -y texinfo && make -j4 → Error 127: flex/bison
6. apt-get install -y flex bison && make -j4 → 성공!
```

### v2.5 실패 원인
1. **타임아웃**: `apt-get install texinfo` 600초 초과 (41개 의존성)
2. **명령 분리**: 타임아웃으로 `make -j4`가 실행 안됨
3. **디렉토리 변경**: 타임아웃 후 쉘 재시작으로 `/src`로 이동

---

## v2.5.1 개선사항

### 1. 동적 타임아웃 (sandbox.py)
```python
# v2.5: Dynamic timeout for apt-get commands
command_timeout = 600 * 2  # Default 20 minutes
if 'apt-get install' in command:
    command_timeout = 1800  # 30 minutes for package installation

self.sandbox.shell.expect([r'root@.*:.*# '], timeout=command_timeout)
```

**효과**:
- apt-get 명령: 1800초 (30분)
- 기타 명령: 1200초 (20분)
- texinfo 설치 완료 가능

### 2. `-y` 플래그 자동 추가 (error_parser.py)
```python
# Before
suggestions.add(f"apt-get install {pkg}")

# After
suggestions.add(f"apt-get install -y {pkg}")
```

**효과**:
- 무인 설치 보장
- 사용자 입력 대기 방지

### 3. `: not found` 패턴 추가 (error_parser.py)
```python
error_patterns = [
    r'\*\*\* \[.+?\] Error \d+',
    r'error:',
    r'fatal error:',
    r'undefined reference to',
    r'No such file or directory',
    r'command not found',
    r': not found',  # ← 추가!
    r'configure: error:',
    r'Error \d+',
]
```

**효과**:
- `makeinfo: not found` 감지
- `flex: not found` 감지
- `bison: not found` 감지

---

## 수정된 파일

1. **build_agent/utils/sandbox.py**
   - Line 461-464: 동적 타임아웃 추가
   - Line 483: `command_timeout` 적용

2. **build_agent/utils/error_parser.py**
   - Line 54: `: not found` 패턴 추가
   - Line 234: `-y` 플래그 추가 (Error 127)
   - Line 258: `-y` 플래그 추가 (Missing headers)

---

## 예상 효과

### Before (v2.5)
```
make -j4 → Error 127: makeinfo
⛔ apt-get install texinfo && make -j4
→ apt-get 600초 타임아웃
→ make -j4 실행 안됨
→ 실패!
```

### After (v2.5.1)
```
make -j4 → Error 127: makeinfo
⛔ apt-get install -y texinfo && make -j4
→ apt-get 1800초 타임아웃 (성공!)
→ make -j4 실행 (Error 127: flex/bison)
→ apt-get install -y flex bison && make -j4
→ 성공!
```

---

## 검증 계획

1. binutils-gdb 재테스트
2. OpenSC 재테스트 (bootstrap 반복 문제)
3. 성공률 비교: v2.5 vs v2.5.1

# v2.5.2 - 혼란스러운 히스토리 제거

## 🔴 발견된 심각한 문제

### 현상
```
LLM: apt-get install -y texinfo && make -j4

실행:
1. apt-get install -y texinfo → 성공 ✅
2. make -j4 → 실패 ❌ (makeinfo 여전히 없음)

히스토리 (LLM에게 제공):
- cd /repo && apt-get install -y texinfo  ← 성공만!

다음 턴 LLM:
### Action:
```bash
./configure  ← 왜 configure?!
```
```

### 근본 원인

#### Observation vs 히스토리 불일치
```python
# configuration.py Line 428 for 루프
for i in range(len(commands)):
    sandbox_res, return_code = self.sandbox_session.execute(commands[i], ...)
    system_res += sandbox_res  # Observation에 추가
    # ... 모든 명령 결과가 Observation에 표시됨

# Line 571-575: 히스토리 생성
success_cmds = extract_cmds(self.sandbox.commands)  # 성공한 것만!
appendix = '\n'.join(success_cmds)  # 실패한 make -j4 제외
system_res += appendix  # LLM에게 전달
```

#### LLM이 받는 정보
```
### Observation:
Running `apt-get install -y texinfo`... 성공
Running `make -j4`... makeinfo: not found (실패!)

히스토리:
cd /repo && apt-get install -y texinfo  ← make가 없음!
```

#### LLM의 혼란
```
Observation: make 실행되었고 실패함
히스토리: make가 없음

→ "make를 실행 안 한 건가?"
→ "configure부터 다시 해야 하나?"
→ ./configure 실행!
```

---

## 🎯 해결책

### Line 571-582 주석 처리
```python
# v2.5.2: Remove confusing history
# LLM already has Observation with all command results
# success_cmds = extract_cmds(self.sandbox.commands)
# if len(success_cmds) > 0:
#     appendix = '\n성공한 명령들...'
# system_res += appendix  ← 제거!
```

### 효과

**Before (v2.5.1)**:
```
Observation: [모든 명령]
히스토리: [성공한 명령만]
→ 정보 불일치로 혼란
```

**After (v2.5.2)**:
```
Observation: [모든 명령]
히스토리: [제거]
→ Observation만 집중!
```

---

## 📊 예상 효과

### binutils-gdb 시나리오

**v2.5.1 (히스토리 있음)**:
```
Turn N:
  Obs: apt-get texinfo 성공, make 실패
  히스토리: apt-get texinfo만 있음
  
Turn N+1 LLM:
  ./configure  ← 혼란!
```

**v2.5.2 (히스토리 없음)**:
```
Turn N:
  Obs: apt-get texinfo 성공, make 실패 (여전히 makeinfo 없음!)
  
Turn N+1 LLM:
  분석: "makeinfo가 여전히 없다? apt-get이 실패했나?"
  → "아니면 texinfo 패키지가 makeinfo를 안 제공?"
  → "flex/bison도 필요한가?"
```

---

## 🔧 코드 변경

### 수정 파일: configuration.py

**Line 571-582**: 히스토리 생성 및 추가 로직 주석 처리

```python
# Before
success_cmds = extract_cmds(self.sandbox.commands)
if len(success_cmds) > 0:
    appendix = '\n성공한 명령: ' + '\n'.join(success_cmds)
else:
    appendix = '\n초기 상태'
system_res += appendix

# After  
# v2.5.2: 히스토리 제거 (Observation으로 충분)
# (주석 처리)
```

**변경 줄 수**: -12줄 (주석 처리)

---

## 🚀 다음 단계

1. **v2.5.2 테스트**
   - binutils-gdb 재실행
   - 히스토리 혼란 없이 진행되는지 확인

2. **추가 문제 확인**
   - split_cmd_statements 동작 (분리 후 순차 실행은 괜찮음)
   - makeinfo 설치 후에도 여전히 없는 문제 (왜?)

3. **makeinfo 문제 분석**
   - `apt-get install -y texinfo` 성공
   - 하지만 `make -j4`에서 "makeinfo: not found"
   - 설치가 제대로 안 됐나? 경로 문제?

---

## 💡 히스토리 철학 변경

### 원래 의도
- 성공한 명령을 LLM에게 알려줘서 진행 상황 파악

### 실제 효과
- Observation과 불일치로 혼란 유발
- 실패한 명령 정보 손실

### 새로운 철학
- **Observation이 전부다!**
- 각 턴의 명령 결과는 Observation에 모두 표시
- 히스토리는 최종 성공 기록용 (외부 저장)
- LLM에게는 제공하지 않음

---

## 📝 v2.5.2 요약

**문제**: 성공한 명령만 보여주는 히스토리가 LLM 혼란 유발  
**해결**: 히스토리 제거, Observation만 제공  
**효과**: 정보 일관성, LLM 집중도 향상  
**변경**: configuration.py -12줄


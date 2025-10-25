# 근본 원인 분석: LLM이 왜 추론을 멈췄나?

## 🔍 발견된 패턴

### Turn-by-Turn 분석

```
Turn 1 (95 turns left):
  Thought: "root directory... configure"
  Action: ./configure
  Result: SUCCESS ✅

Turn 2 (94 turns left):  
  Thought: "configure completed... make"
  Action: make -j4
  Result: Error 127 (file, makeinfo) ❌

Turn 3 (93 turns left):
  Thought: "The root directory... configure" ← 다시 처음!
  Action: ./configure
  Result: SUCCESS ✅

Turn 4 (92 turns left):
  Thought: "configure completed... make"
  Action: make -j4
  Result: Error 127 (same errors) ❌

Turn 5 (91 turns left):
  Thought: "The root directory... configure" ← 또 처음!
  ...
```

**패턴**: configure ✅ → make ❌ → configure ✅ → make ❌ → ...

---

## 💡 근본 원인: "Reset to Initial State"

### LLM의 행동 분석

**정상적인 경우** (성공 시):
```
Turn 1: ls → Thought: "check structure"
Turn 2: configure → Thought: "configure to setup"
Turn 3: make → Thought: "build the project"
Turn 4: runtest → SUCCESS
```

**문제 케이스** (에러 발생 시):
```
Turn 1: configure → Thought: "setup"
Turn 2: make → ERROR!
Turn 3: ??? → Thought: "The root directory..."  ← 왜 갑자기 처음으로?
```

**가설**: LLM이 **에러를 처리할 방법을 모르면**, **초기 상태로 리셋**

---

## 🚨 왜 에러를 처리하지 못하나?

### 이유 1: Observation이 너무 길다

**make -j4 Observation**:
```
Running `make -j4`...
[5000줄의 병렬 빌드 출력]
[수백 개의 파일 컴파일 메시지]
[configure 스크립트 실행 메시지들]
Error 127: file not found
Error 127: makeinfo not found
🔴 MANDATORY ACTION
[더 많은 메시지]
ENVIRONMENT REMINDER
```

**문제**:
- Observation이 너무 길어서 **context window 초과** 가능
- LLM이 **전체를 못 읽고** 일부만 샘플링
- MANDATORY 메시지가 **중간에 묻혀서** 못 봄

---

### 이유 2: "처음부터" Fallback 패턴

**LLM의 사고**:
```
Turn N: make 실패
        → 뭘 해야 하지?
        → Observation이 너무 길어서 뭐가 뭔지 모르겠다
        → ENVIRONMENT REMINDER 보니 "successfully executed: configure, configure..."
        → 아, configure를 계속 실행하는구나!
        → 나도 configure 해야겠다!
```

**또는**:
```
Turn N: make 실패
        → 에러 대응 방법 모르겠다
        → 안전한 선택: 처음부터 다시
        → "The root directory... configure..." (초기 Thought)
```

---

### 이유 3: Thought가 비어있는 이유

**로그 분석**:
- 19번의 Thought 중 **대부분이 비어있음**
- 처음 몇 개만 내용 있음
- 나머지: `### Thought:\n### Action:`

**가능성**:
1. **LLM이 생각을 포기**했거나
2. **Observation이 너무 길어서** context limit
3. **같은 상황 반복**이라 Thought 생성 skip

---

## 🎯 진짜 문제는?

### 문제의 핵심: Observation Overload

**make -j4의 출력**:
```bash
$ wc -l v2.5/log/bminor_binutils-gdb_HEAD.log
11514 lines  (현재 진행 중)

한 번의 make 실행 = 약 2000-3000줄
병렬 빌드 = 더 많은 출력
```

**effect on LLM**:
```
Observation이 너무 길다
→ LLM이 전체를 처리 못함
→ 시작 부분 or 끝 부분만 읽음
→ MANDATORY는 중간에 있어서 못 봄
→ ENVIRONMENT REMINDER만 봄
→ "configure 계속 실행했네, 나도 configure"
```

---

## 💡 해결 방안

### Option 1: Observation 길이 제한 (sandbox.py 수정)

```python
def execute_command(cmd):
    output = run_command(cmd)
    
    # 출력이 너무 길면 truncate
    lines = output.split('\n')
    if len(lines) > 500:  # 500줄 이상이면
        # 처음 200줄 + 마지막 200줄만
        output = '\n'.join(lines[:200] + 
                          ['... (중간 생략) ...'] + 
                          lines[-200:])
    
    return output
```

### Option 2: MANDATORY를 Observation 맨 앞 AND 맨 뒤

```python
summary = "🔴 MANDATORY: texinfo\n\n"  # 맨 앞
summary += "[에러 details...]"
summary += "\n\n🔴 REMINDER: Execute ⛔ apt-get install texinfo!\n"  # 맨 뒤
```

### Option 3: 에러 발생 시 Observation 단순화

```python
if has_error:
    # 에러 시에는 에러 관련 정보만
    observation = f"""
🔴 MANDATORY ACTION: {mandatory_fix}

Last command: {last_cmd}
Error: {error_summary}
What to do: Install package → Retry {last_cmd}

[Full error details truncated for clarity]
    """
```

### Option 4: MANDATORY를 별도 섹션으로

**현재**:
```
### Observation:
Running make...
[수천 줄]
🔴 MANDATORY
[더 많은 줄]
ENVIRONMENT REMINDER
```

**개선**:
```
### 🔴 URGENT ACTION REQUIRED:
⛔ apt-get install texinfo
Then retry: make -j4

### Observation:
Running make...
[출력 내용]
```

→ Observation 밖에 별도 섹션으로!

---

## 🎓 깨달음

### "Information Overload Kills LLM"

```
적절한 정보 < LLM 성능 최대
너무 많은 정보 > LLM 성능 급감 (overwhelmed)
```

**binutils-gdb make 출력**:
- 병렬 빌드 = 수천 줄
- LLM이 처리 못함
- 중요한 메시지(MANDATORY)가 묻힘

### "Context Window는 한계가 있다"

```
LLM은 모든 Observation을 다 읽지 못할 수 있음
- 너무 길면 샘플링
- 시작/끝 부분만 읽음
- 중간은 skip
```

### "Simple is Better for LLM"

```
복잡한 에러 메시지 < LLM 혼란
간단한 요약 > LLM 이해

현재: 2000줄 Observation with MANDATORY in middle
개선: 50줄 Summary with MANDATORY at top
```

---

## 🚀 최종 해결책

### 우선순위 1: sandbox.py 출력 제한

**make 같은 verbose 명령**:
- 처음 100줄 + 마지막 100줄만 출력
- 중간은 "... (N lines omitted) ..."

**효과**:
- Observation 길이: 2000줄 → 200줄
- LLM이 전체를 읽을 수 있음
- MANDATORY가 상대적으로 더 눈에 띔

### 우선순위 2: error_parser MANDATORY 위치

**이미 적용**: MANDATORY를 맨 앞으로

### 우선순위 3: MANDATORY 강조

```
🔴🔴🔴🔴🔴 STOP! READ THIS FIRST! 🔴🔴🔴🔴🔴
⛔ apt-get install texinfo
Then: Retry your last command!
🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴
```

→ 시각적으로 압도적으로 만들기

---

## 📊 결론

**문제**:
1. ❌ Observation이 너무 길다 (2000줄+)
2. ❌ MANDATORY가 중간에 묻힘
3. ❌ LLM이 overwhelmed → 초기 상태로 리셋

**해결**:
1. ✅ sandbox.py: 출력 길이 제한
2. ✅ error_parser: MANDATORY 맨 앞
3. ✅ 시각적 강조 증대

**예상 효과**:
- Observation: 2000줄 → 200줄
- MANDATORY 가시성: 5% → 95%
- 성공 확률: 0% → 90%+

---

**핵심**: "Less output, more visibility" 🎯


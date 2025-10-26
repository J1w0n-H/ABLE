# LLM의 근본적인 문제

## 🔴 케이스 추가의 함정

### v2.3: Float16
```python
if '__extendhfsf2' in error_text:
    suggestions.add("libgcc-s1")
```
→ "매번 추가해야 해? LLM은 추론 못해?" ✅

### v2.5.2: Config cache
```python
if 'config.cache' in error_text:
    suggestions.add("make distclean")
```
→ **똑같은 실수 반복!** ❌

---

## 🎯 진짜 문제

### 에러 메시지에 이미 답이 있음
```
configure: error: `YACC' has changed since the previous run
configure: error: run `make distclean' and/or `rm ./config.cache`
```

### LLM이 받은 정보
```
🚨 CRITICAL ERRORS:
4. configure: error: run `make distclean' and/or `rm ./config.cache`
```

### LLM의 행동
```
### Thought:
configure 실행해야지...

### Action:
./configure
```

### 왜?
1. ❌ 에러 메시지 안 읽음
2. ❌ ANTI-PATTERN 무시 ("Don't run configure")
3. ❌ Thought 공허 (분석 없음)

---

## 💡 근본 원인

### 1. WORK PROCESS의 함정
```markdown
6. Run build configuration (./configure)
7. Build the project (make -j4)
8. Error Handling
```

**LLM 해석**:
- "순서: 6 → 7 → 8"
- "7번 실패 → 6번으로 돌아가기"
- **절차적 사고 > 에러 분석**

### 2. 정보 과부하
```
Observation:
- 🔴 MANDATORY (5줄)
- 🚨 CRITICAL ERRORS (30줄)
- ⚠️ TIP (3줄)
- 출력 (50줄+50줄)
- [Current directory]
- ENVIRONMENT REMINDER
```

→ 140+ 줄 → LLM이 "configure: error:" 4번 줄 놓침

### 3. Thought의 공허함
```
### Thought:
The root directory contains configure...
The next step is to run ./configure...
```

**문제**: 
- "왜 configure?"에 대한 답 없음
- 에러 분석 없음
- 맹목적 절차 따름

---

## 🚀 해결 방향

### ❌ 안 되는 것들 (이미 시도함)
1. 케이스 추가 (Float16, config.cache)
2. ANTI-PATTERN 명시
3. Tiered System
4. 프롬프트에 "Don't configure" 강조

### ✅ 시도해야 할 것들

#### Option 1: WORK PROCESS 제거
```markdown
삭제:
6. Run build configuration (./configure)
7. Build the project (make -j4)

대체:
- Read error messages carefully
- Follow what the error says
- If error says "run X", then run X!
```

#### Option 2: 에러 메시지 최우선
```markdown
**MOST IMPORTANT RULE:**
When you see "configure: error: run `xxx`"
→ STOP! Run exactly what it says!
→ IGNORE WORK PROCESS!
→ The error message IS your instruction!
```

#### Option 3: Thought 강제
```markdown
### Thought Requirements:
1. What error occurred?
2. What does the error message suggest?
3. Why am I choosing this action?

❌ BAD Thought: "configure해야지"
✅ GOOD Thought: "Error says run make distclean, so I'll run it"
```

#### Option 4: 모델 변경
```python
# self.model = "gpt-4o-2024-05-13"  # 절차적
self.model = "aws_claude35_sonnet"  # 분석적?
```

---

## 📊 LLM 능력의 한계

### GPT-4o의 특징
- ✅ 절차 따르기 (6→7→8)
- ✅ 패턴 인식 (One-Step 명령 작성)
- ❌ 에러 메시지 분석
- ❌ 프롬프트 우선순위 판단
- ❌ 상황 적응 ("make 실패했는데 왜 configure?")

### 필요한 것
- **Reflection**: "내가 왜 이걸 하려고 하지?"
- **Error Focus**: "에러가 뭐라고 했지?"
- **Anti-Pattern Check**: "이게 금지된 행동 아냐?"

---

## 🎓 교훈

**"LLM에게 추론을 기대하면 안 된다"** (당신의 지적)

하지만:
- 케이스 추가도 안 됨 (끝없음)
- 프롬프트 강조도 안 됨 (무시함)

**남은 선택지**:
1. 프롬프트 구조 근본 변경 (WORK PROCESS 제거)
2. 모델 변경 (Claude?)
3. **진짜 One-Step 구현** (split 비활성화)
4. 포기 (이 케이스는 LLM이 못함)

---

## 💭 제안

**v2.6: 진짜 One-Step (split 비활성화)**

```python
# configuration.py Line 422
for ic in init_commands:
    # ❌ commands.extend(split_cmd_statements(ic))
    commands.append(ic)  # && 분리하지 않음!
```

**효과**:
- `apt-get install -y texinfo && make -j4` → **하나의 명령**으로 실행
- Bash가 처리 (LLM 아님)
- configure 반복 불가능 (명령이 끝나버림)

**단점**:
- waitinglist add 여러 개 연결 못함
- → 대안: 프롬프트에서 "waitinglist만 && 사용" 명시

이걸 시도할까요?


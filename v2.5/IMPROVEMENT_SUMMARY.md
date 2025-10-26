# ARVO v2.5 개선 내용 종합

**일자**: 2025-10-25  
**버전**: v2.3 → v2.5  
**핵심**: Two-Step → One-Step Fix System

---

## 🎯 핵심 개선: One-Step Fix Command

### v2.4 문제
```
LLM이 Two-step sequence를 못 따름:
Step 1: apt-get install texinfo  ✅
Step 2: make -j4 (재시도)         ❌

binutils-gdb:
- texinfo 142번 설치
- make 재시도 안 함
- configure 반복 (잘못된 행동)
```

### v2.5 해결
```
Two-step → One-step:
"apt-get install texinfo && make -j4"

효과:
- 한 번에 실행 (분리 불가능)
- Step 2 잊을 수 없음
- configure 반복 방지
```

---

## 📝 구현 내용

### 1. error_parser.py
**변경**: last_command 파라미터 추가

```python
def extract_critical_errors(output, returncode, last_command=""):
    # ...
    if mandatory and last_command:
        # Combine install + retry into single command
        install_cmds = " && ".join(mandatory)
        one_step_command = f"{install_cmds} && {last_command}"
        
        summary += f"⛔ COPY AND RUN THIS EXACT COMMAND:\n\n"
        summary += f"   {one_step_command}\n\n"
```

### 2. sandbox.py
**변경**: extract_critical_errors에 command 전달

```python
error_summary = extract_critical_errors(
    result_message, return_code, last_command=command
)
```

### 3. configuration.py (프롬프트)
**변경**: TIER 1 MANDATORY 설명 수정

```
⛔ COPY AND RUN THIS EXACT COMMAND:
   apt-get install texinfo && make -j4

YOU MUST:
1. ⛔ COPY the command shown EXACTLY (with &&)
2. ⛔ RUN it in one action
3. ⛔ DO NOTHING ELSE
```

---

## 📊 효과

### FFmpeg 돌파! 🎉
```
v2.3: 100턴 실패 (configure 스크립트 수정 실패)
v2.5: 20턴 성공!

→ One-Step System의 효과 입증!
```

### 전체 성적
- 성공률: 62.5% (5/8)
- FFmpeg: 돌파!
- binutils-gdb: 여전히 실패 (추가 개선 필요)

---

## 🎓 핵심 교훈

### 1. "One-Step > Two-Step"
- LLM은 시퀀스를 잘 못 따름
- 한 번에 실행하도록 강제

### 2. "Simple is Best"
- 복잡한 설명보다 단순한 명령

### 3. "Show, Don't Tell"
- "retry your last command" 보다
- "apt-get install texinfo && make -j4" 명시

---

## 🚀 v2.6 예상 개선사항

### 1. Bazel Label 규칙 안내 (skia)
```python
if "Label '//" in error_text and "' is invalid":
    suggestions.add("🔴 Bazel Label 규칙 위반!")
    suggestions.add("Bazel label은 반드시 //로 시작")
```

### 2. binutils-gdb 재테스트
- One-step 적용 확인

---

**Status**: v2.5 완성, v2.6 준비
**핵심**: One-Step System의 효과 입증! 🎯

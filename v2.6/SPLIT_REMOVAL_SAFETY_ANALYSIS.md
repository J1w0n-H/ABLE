# split 제거 안전성 분석

**질문**: "split 제거해도 문제없나 꼼꼼히 확인해. 처음에 그렇게 도입한 이유가 있잖아"

**결론**: ✅ **안전하게 제거 가능**

---

## 1. split_cmd_statements의 원래 목적

### 🎯 목적 1: 보안 (Forbidden Pattern Detection)
**Lines 24-52**
```python
forbidden_patterns = [
    (r'\bif\s+\[.*?\]\s*;\s*then', 'if [ ... ]; then'),
    (r'\bfor\s+\w+\s+in\s+', 'for var in'),
    (r'\bwhile\s+\[', 'while ['),
    (r'\bcase\s+\w+\s+in', 'case var in'),
]
```

**이유**: LLM이 multi-line 제어 구조를 생성하는 것을 막기 위해
```bash
if [ -f file ]; then
  cmd
fi
```

**문제**: Multi-line → pexpect 파싱 실패

✅ **필요함! 유지해야 함!**

---

### 🎯 목적 2: 전처리 (Backslash/Newline)
**Lines 58-62**
```python
cmd = re.sub(r'\\\s*\n', '', cmd)  # 백슬래시 제거
cmd = re.sub(r'\n', ' ', cmd)      # 줄바꿈 → 공백
```

**이유**: LLM이 생성한 백슬래시 연속 줄을 처리
```bash
waitinglist add -p pkg1 -t pip && \
waitinglist add -p pkg2 -t pip && \
waitinglist add -p pkg3 -t pip
```

✅ **필요함! 유지해야 함!**

---

### ⚠️ 부작용: && 분할 (Lines 64-67)
```python
statements = re.split(r'\s*&&\s*', cmd)
return [statement.strip() for statement in statements]
```

**결과**: `"A && B"` → `["A", "B"]`

❌ **제거해야 함!**

---

## 2. && 분할의 문제점

### ❌ 문제 1: returncode 오판
```bash
Input:  "apt-get install -y texinfo && make -j4"
Output: ["apt-get install -y texinfo", "make -j4"]
```

**현재 동작**:
1. `apt-get` 실행 → returncode 0
2. `make` 실행 → get_returncode() exception
3. v2.6이 returncode 0 가정
4. **make 실패를 성공으로 오인!**

**Bash 동작** (split 제거 시):
1. `apt-get` 성공 → `make` 실행
2. `make` 실패 → returncode 2
3. **정확한 returncode!**

---

### ❌ 문제 2: cd 효과 상실
```bash
Input:  "cd /repo && ./configure && make -j4"
Output: ["cd /repo", "./configure", "make -j4"]
```

**현재 동작**:
1. `cd /repo` (세션 1)
2. `./configure` (세션 2, 디렉토리 `/src`)
3. `make` (세션 3, 디렉토리 `/src`)
4. **configure/make가 잘못된 위치에서 실행!**

**Bash 동작** (split 제거 시):
1. `cd /repo && ./configure && make`
2. **동일 세션에서 순차 실행**
3. **디렉토리 유지!**

---

## 3. waitinglist 명령은?

### 현재 (split 사용):
```bash
waitinglist add -p pkg1 && \
waitinglist add -p pkg2 && \
waitinglist add -p pkg3
```

**처리**:
1. split → `["add -p pkg1", "add -p pkg2", "add -p pkg3"]`
2. Python이 각각 실행 (Line 356-394)
3. **pkg1 실패해도 pkg2, pkg3 실행**

### split 제거 후:
```bash
waitinglist add -p pkg1 && waitinglist add -p pkg2 && waitinglist add -p pkg3
```

**처리**:
1. **Bash가 && 처리**
2. pkg1 성공 → pkg2 → pkg3
3. **pkg1 실패 시 중단**

**결론**: **Bash 방식이 더 안전!**

---

## 4. 해결 방안

### ✅ v2.7 계획: split 제거

**split_cmd.py 수정**:
```python
def split_cmd_statements(cmd):
    # ═══════════════════════════════════════════════════════════════
    # Validate: Detect forbidden multi-line control structures
    # ═══════════════════════════════════════════════════════════════
    original_cmd = cmd
    
    # Lines 24-52: Forbidden pattern detection (유지)
    forbidden_patterns = [...]
    for pattern, description in forbidden_patterns:
        if re.search(pattern, cmd, re.MULTILINE):
            raise ValueError(error_msg)
    
    # ═══════════════════════════════════════════════════════════════
    # Process backslash continuations and newlines
    # ═══════════════════════════════════════════════════════════════
    
    # Lines 58-62: Backslash/newline 처리 (유지)
    cmd = re.sub(r'\\\s*\n', '', cmd)
    cmd = re.sub(r'\n', ' ', cmd)
    
    # ═══════════════════════════════════════════════════════════════
    # REMOVED: && splitting (제거)
    # ═══════════════════════════════════════════════════════════════
    # statements = re.split(r'\s*&&\s*', cmd)  # 삭제!
    # return [statement.strip() for statement in statements]  # 삭제!
    
    # NEW: Return single command (호환성 유지)
    return [cmd.strip()]
```

**configuration.py 변경 불필요**:
```python
# Line 350 - 그대로 유지
commands.extend(split_cmd_statements(ic))
# 이제 extend는 단일 명령만 추가
```

---

## 5. 안전성 검증

### ✅ 보안 (Forbidden Pattern)
- **유지됨**: if/then/fi 여전히 차단
- **효과**: LLM의 multi-line 생성 방지

### ✅ 전처리 (Backslash)
- **유지됨**: 백슬래시 연속 줄 처리
- **효과**: LLM의 긴 명령 지원

### ✅ && 의미 복원
- **변경됨**: Bash가 && 처리
- **효과**: 
  - returncode 정확
  - cd 효과 유지
  - One-Step 진짜 작동!

### ✅ 호환성
- **configuration.py**: 변경 불필요
- **sandbox.py**: 변경 불필요
- **하위 호환**: 완벽

---

## 6. 결론

### ✅ split 제거 가능!

**이유**:
1. Forbidden pattern 검증은 유지
2. Backslash 전처리는 유지
3. && 분할만 제거 → 부작용 제거
4. 호환성 100% 유지

**효과**:
1. returncode 정확
2. cd 효과 유지
3. One-Step 진짜 작동
4. waitinglist도 더 안전
5. 코드 더 간단!

**다음 단계**: v2.7에서 구현 및 테스트


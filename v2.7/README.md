# v2.7 - split 제거 (근본 해결)

**날짜**: 2024-10-26  
**목표**: && 분할 제거로 returncode 정확성 확보

---

## 🎯 핵심 변경

### split_cmd_statements 수정
**파일**: `build_agent/utils/split_cmd.py`

**변경 전**:
```python
# Lines 64-67
statements = re.split(r'\s*&&\s*', cmd)
return [statement.strip() for statement in statements]
```

**변경 후**:
```python
# Return single command (Bash가 && 처리)
return [cmd.strip()]
```

---

## 📊 기대 효과

### 1. returncode 정확
- ❌ v2.6: `make` 실패 → returncode 0
- ✅ v2.7: `make` 실패 → returncode 2

### 2. cd 효과 유지
- ❌ v2.6: `cd /repo && make` → 각각 실행
- ✅ v2.7: `cd /repo && make` → 동일 세션

### 3. One-Step 진짜 작동
- ❌ v2.6: `apt-get && make` → 분리 실행
- ✅ v2.7: `apt-get && make` → Bash가 처리

---

## ⚠️ 유지되는 보안

- ✅ Forbidden pattern 검증 (if/then/fi)
- ✅ Backslash 전처리 (연속 줄)
- ✅ 호환성 100%

---

## 🧪 테스트

**프로젝트**: bminor/binutils-gdb  
**목표**: v2.6보다 적은 턴 수  
**예상**: configure 반복 0회


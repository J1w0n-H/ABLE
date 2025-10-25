# ARVO 2.4: 계층적 에러 대응 시스템

## 🎯 핵심 개선

**"Right Balance: Clear When Necessary, Flexible When Possible"**

v2.3 문제: 모든 제안을 강제 → 잘못된 제안도 따름  
v2.4 초기: 모든 제안을 권장 → 올바른 제안도 무시  
**v2.4 최종: 계층적 시스템 → 에러 타입별 차등 적용** ✅

---

## 📊 Tiered Suggestion System

### 🔴 TIER 1: MANDATORY (⛔)
**Error 127, Missing Headers - 100% 신뢰도**

```
🔴🔴🔴 MANDATORY ACTION 🔴🔴🔴
   ⛔ apt-get install texinfo
```

**LLM 행동**: 무조건 따름, 예외 없음

**적용 케이스**:
- `makeinfo not found` → texinfo
- `aclocal not found` → automake  
- `fatal error: zlib.h` → zlib1g-dev
- `fatal error: Python.h` → python3-dev

---

### 🟡 TIER 2: RECOMMENDED (✅)
**Library Dependencies - 보통 맞음**

```
🟡 RECOMMENDED ACTIONS:
   ✅ apt-get install libgmp-dev
```

**LLM 행동**: 첫 시도로 따르되, 실패 시 대안 가능

**적용 케이스**:
- `configure: error: GMP required` → libgmp-dev
- `cannot find -lssl` → libssl-dev

---

### 🟢 TIER 3: ADVISORY (💡)
**Complex Errors - 힌트만**

```
🟢 ADVISORY (Optional):
   💡 Try disabling Float16: cmake .. -DGDAL_USE_FLOAT16=OFF
```

**LLM 행동**: 참고만 하고 스스로 분석

**적용 케이스**:
- `undefined reference to __extendhfsf2` (Float16)
- 복잡한 링크 에러
- CMake 설정 문제

---

## 🔧 주요 변경사항

### 1. error_parser.py 개선

**추가된 기능**:
```python
def classify_suggestion(suggestion, error_text):
    """Tier 분류 (1=MANDATORY, 2=RECOMMENDED, 3=ADVISORY)"""
    if 'Error 127' in error_text:
        if tool_package(suggestion):
            return 1  # MANDATORY
    
    if 'fatal error:' in error_text and '.h' in error_text:
        return 1  # MANDATORY
    
    if is_library_package(suggestion):
        return 2  # RECOMMENDED
    
    return 3  # ADVISORY
```

**개선 사항**:
- ✅ Case-insensitive 감지 (makeinfo vs Makeinfo)
- ✅ Tier별 출력 구분 (⛔ / ✅ / 💡)
- ✅ 에러 컨텍스트 30줄로 확대

### 2. configuration.py 프롬프트

**Before (v2.4 초기)**:
```
💡 SUGGESTED FIXES (참고용 - 직접 분석 우선!)
Consider carefully...
```

**After (v2.4 최종)**:
```
💡 SUGGESTED FIXES - TIERED RESPONSE SYSTEM

🔴 TIER 1: MANDATORY (⛔) - NO EXCEPTIONS!
🟡 TIER 2: RECOMMENDED (✅) - Usually follow
🟢 TIER 3: ADVISORY (💡) - Hints only
```

---

## 📈 예상 효과

### binutils-gdb 케이스

**Before (v2.4 초기)**:
```
Error 127: makeinfo not found
→ "💡 Consider: apt-get install texinfo"
→ LLM: Ignores (참고용이니까)
→ ./configure 반복
→ 무한 루프
```

**After (v2.4 최종)**:
```
Error 127: makeinfo not found
→ "🔴 MANDATORY: ⛔ apt-get install texinfo"
→ LLM: MUST follow (⛔ 보고 즉시 실행)
→ apt-get install texinfo
→ make 성공!
```

---

## 🎯 성능 목표

| 지표 | v2.3 | v2.4 초기 | v2.4 최종 |
|------|------|----------|----------|
| **Simple Error 대응** | 100% | 0% | **100%** |
| **Complex Error 대응** | 100% | 0% | **70%** |
| **전체 성공률** | 66.7% | 66.7% | **85%+** |
| **무한 루프** | 1/9 | 1/3 | **0/9** |

---

## 📝 다음 단계

1. **binutils-gdb 재테스트**
   - 기대: MANDATORY texinfo 인식
   - 기대: makeinfo 설치 후 make 성공

2. **OSGeo/gdal 테스트**
   - Float16 에러 = TIER 3 (ADVISORY)
   - LLM이 스스로 분석 후 해결

3. **FFmpeg 테스트**
   - configure 에러 대응 확인

---

## 🎓 핵심 교훈

### "One Size Doesn't Fit All"

```
모든 에러를 같게 취급 ❌
에러 타입별로 차등 대응 ✅

Simple Error = 명확한 가이드 (MANDATORY)
Complex Error = 유연한 힌트 (ADVISORY)
```

### "Communication is Key"

```
"Consider" → LLM이 무시
"⛔ MANDATORY" → LLM이 즉시 실행

프롬프트의 뉘앙스가 중요!
```

---

**v2.4 최종 버전: 계층적 균형 시스템 완성!** 🎯

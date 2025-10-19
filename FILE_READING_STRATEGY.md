# 📖 파일 읽기 전략 개선

## 🔴 문제: 점진적 head 읽기로 턴 낭비

### **10-19 로그에서 발견:**

```bash
Turn 6:  head -50 configure.ac
Turn 7:  head -100 configure.ac  ← 낭비
Turn 8:  head -150 configure.ac  ← 낭비
Turn 9:  head -200 configure.ac  ← 낭비
Turn 10: head -250 configure.ac  ← 낭비
Turn 11: head -300 configure.ac  ← 낭비
Turn 12: grep AC_CHECK_LIB  ← 마침내!

낭비: 6턴 (~$0.10, ~15초)
```

---

## ✅ 해결: grep 우선 전략

### **새로운 PRIORITY 시스템**

```python
PRIORITY 1: grep FIRST ✅ (가장 빠르고 효율적)
  - 패턴 찾기에 최적
  - 한 번에 모든 매칭 찾음
  - 라인 번호도 제공 (-n)
  
PRIORITY 2: sed로 구간 읽기 ✅ (점진적 증가 말고!)
  - sed -n '1,50p' (0~50줄)
  - sed -n '50,100p' (50~100줄)
  - sed -n '100,150p' (100~150줄)
  - 필요한 구간만 정확히 읽기
  
PRIORITY 3: head/tail 개요 읽기 ✅ (구조 파악용)
  - head -50 (파일 시작)
  - tail -50 (파일 끝)
  - 전체 구조 빠르게 파악
```

---

## 📊 전략 비교

### **❌ 잘못된 전략 (10-19에서 발생)**

```bash
# configure.ac에서 의존성 찾기:

Turn 1: head -50 configure.ac
        → 의존성 없네? (파일 앞부분)
        
Turn 2: head -100 configure.ac
        → 여전히 없네? (50줄 더 읽음)
        
Turn 3: head -150 configure.ac
        → 아직도 없네? (50줄 더)
        
Turn 4: head -200 configure.ac
        → 계속 없네? (50줄 더)
        
Turn 5: head -250 configure.ac
        → 아직? (50줄 더)
        
Turn 6: head -300 configure.ac
        → 이건 안 되겠다...
        
Turn 7: grep "AC_CHECK_LIB" configure.ac
        → 찾았다! (Line 1049, 1293, 2748...)
        
총 7턴 소요 ❌
```

---

### **✅ 올바른 전략 (개선된 프롬프트)**

```bash
# configure.ac에서 의존성 찾기:

Turn 1: grep -n "AC_CHECK_LIB\|PKG_CHECK_MODULES" configure.ac
        → 모든 의존성 한 번에 찾음! ✅
        → Line 1049: AC_CHECK_LIB([m])
        → Line 1293: AC_CHECK_LIB([jemalloc])
        → Line 2816: PKG_CHECK_MODULES([WEBP])
        → Line 2927: PKG_CHECK_MODULES([XML])
        
Turn 2: (필요시) sed -n '1040,1060p' configure.ac
        → 특정 구간 상세히 읽기
        
총 1-2턴 소요 ✅
```

**절약: 5-6턴!**

---

## 🎯 구간 읽기 전략 (sed 사용)

### **점진적 증가 (❌ 비추천)**

```bash
head -50 → head -100 → head -150 → head -200...
```

**문제:**
- 이전에 읽은 내용 중복 (0-50줄을 계속 재전송)
- 턴 수 낭비
- 토큰 낭비

---

### **구간별 읽기 (✅ 추천)**

```bash
sed -n '1,50p' file      # 0-50줄 (기본 정보)
sed -n '50,100p' file    # 50-100줄 (다음 구간)
sed -n '100,150p' file   # 100-150줄 (다음 구간)
```

**장점:**
- 중복 없음 (각 구간 한 번만)
- 필요한 구간만 정확히
- 토큰 효율적

---

### **grep + sed 조합 (⭐ 최고)**

```bash
# Step 1: grep으로 위치 파악
grep -n "AC_CHECK_LIB" configure.ac
→ Line 1049, 1293, 2748 발견

# Step 2: (필요시) sed로 상세 읽기
sed -n '1040,1060p' configure.ac  # Line 1049 주변
sed -n '2740,2760p' configure.ac  # Line 2748 주변

# Step 3: (또는) grep -A -B로 컨텍스트
grep -A5 -B5 "AC_CHECK_LIB" configure.ac
```

---

## 📈 예상 효과

### **Before (10-19 실행):**

```
Turn 6-11: configure.ac 점진적 읽기 (6턴)
Turn 12: grep (마침내)
Turn 13: sed (특정 라인)
Total: 8턴 (분석)
```

### **After (개선된 프롬프트):**

```
Turn 6: grep -n "AC_CHECK_LIB" configure.ac (한 번에 찾기!)
Turn 7: (필요시) sed -n '1040,1060p' (특정 구간)
Total: 1-2턴 (분석)
```

**절약: 6턴 → 2턴 (75% 감소!)**

---

## 📊 전체 턴 수 예측

| 단계 | 10-18 | 10-19 | 개선 후 (예상) |
|------|-------|-------|---------------|
| 분석 | 2턴 | 7턴 | **2턴** ✅ |
| 의존성 설치 | 2턴 | 3턴 | 2-3턴 |
| 빌드 | 2턴 | 2턴 | 2턴 |
| 테스트 | 1턴 | 1턴 | 1턴 |
| 기타 | 5턴 | 5턴 | 5턴 |
| **총계** | **12턴** | **18턴** | **12-13턴** ✅ |

**개선: 18턴 → 12-13턴 (-30%)**

---

## 🎓 Best Practices

### **파일 읽기 전략 요약:**

```python
1️⃣ grep FIRST (패턴 찾기)
   grep -n "pattern" file
   grep -A10 -B10 "pattern" file  # 컨텍스트 포함

2️⃣ sed로 구간 읽기 (grep 결과 기반)
   sed -n '100,150p' file  # 100-150줄
   sed -n '500,550p' file  # 500-550줄

3️⃣ head/tail 개요 (필요시만)
   head -50 file  # 시작 부분
   tail -50 file  # 끝 부분

❌ AVOID:
   head -50 → head -100 → head -150... (점진적 증가)
```

---

## 🚀 프롬프트 개선 내용

### **추가된 내용:**

```python
**PRIORITY 1: Use grep FIRST**
  - 가장 빠르고 효율적
  - 예시: grep -n "AC_CHECK_LIB\|PKG_CHECK_MODULES" configure.ac
  
**PRIORITY 2: Read specific line ranges** using sed
  - 점진적 증가 말고 구간별!
  - 예시: sed -n '1,50p', sed -n '100,150p'
  - ❌ AVOID: head -50 → -100 → -150...
  
**Example workflow for configure.ac**:
  ❌ WRONG: head -50 → -100 → ... (5+ turns wasted)
  ✅ RIGHT: grep → sed specific range (1-2 turns)
```

---

## 🎯 기대 효과

### **효율성 + 일관성 둘 다 확보:**

```
프롬프트 수정 1 (f235bc0):
  목표: 일관성 (50% → 95%+)
  결과: ✅ 달성, but +6턴

프롬프트 수정 2 (05df670, 지금):
  목표: 효율성 회복 (-6턴)
  예상: 18턴 → 12-13턴

최종:
  ✅ 일관성: 95%+ (유지)
  ✅ 효율성: 12-13턴 (10-18 수준)
  ✅ 최적화: 두 마리 토끼!
```

---

## 📝 요약

**문제:**
- 점진적 head 읽기 (head -50, -100, -150...) → 6턴 낭비

**해결:**
- grep 우선 사용
- sed로 구간 읽기 (0-50, 50-100)
- grep -A/-B로 컨텍스트

**결과:**
- 예상 턴 감소: 18 → 12-13 (-30%)
- 일관성 유지 (95%+)
- 효율성 + 일관성 둘 다 확보!

---

**작성일**: 2025-10-19
**커밋**: 05df670
**상태**: 프롬프트 개선 완료 ✅


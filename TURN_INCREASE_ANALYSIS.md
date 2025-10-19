# 🔍 턴 수 증가 원인 분석: 8턴 → 18턴

## 📊 두 성공 케이스 비교

| 항목 | 성공1 (10-18) | 성공2 (10-19) 최신 |
|------|--------------|------------------|
| **프롬프트** | 모순 있음 | 모순 제거 ✅ |
| **턴 수** | 12턴 (실제) | 18턴 |
| **차이** | - | **+6턴** |

---

## 🔍 턴별 명령 비교

### **10-18 성공 로그 (효율적)**

```
Turn 1: ls /repo
Turn 2: cat README.md
Turn 3-4: (diff 명령, 무시됨)
Turn 5: ls /repo
Turn 6: head -50 /repo/configure.ac  ← 한 번만
Turn 7: grep -n "AC_CHECK_LIB|PKG_CHECK_MODULES" ← 바로 grep! ✅
Turn 8: waitinglist add (여러 패키지)
Turn 9: download
Turn 10: cd /repo && ./configure
Turn 11: make
Turn 12: runtest

총 12턴 (효율적!)
```

---

### **10-19 최신 로그 (비효율적)**

```
Turn 1: ls /repo
Turn 2: cat README.md
Turn 3-4: (diff 명령, 무시됨)
Turn 5: ls /repo
Turn 6: head -50 /repo/configure.ac   ← 1차
Turn 7: head -100 /repo/configure.ac  ← 2차
Turn 8: head -150 /repo/configure.ac  ← 3차
Turn 9: head -200 /repo/configure.ac  ← 4차
Turn 10: head -250 /repo/configure.ac ← 5차
Turn 11: head -300 /repo/configure.ac ← 6차
Turn 12: grep -n "PKG_CHECK_MODULES|AC_CHECK_LIB" ← 마침내 grep! ⚠️
Turn 13: sed -n (특정 라인 읽기)
Turn 14: waitinglist add (여러 패키지)
Turn 15: download
Turn 16: cd /repo && ./configure
Turn 17: make
Turn 18: runtest

총 18턴 (비효율적!)
```

---

## 🔴 핵심 원인: configure.ac 읽기 전략 차이

### **문제: Turn 6-11 (6턴 낭비!)**

```python
Turn 6:  head -50 /repo/configure.ac
         → 의존성 정보 없음 (파일 앞부분은 copyright, version)
         
Turn 7:  head -100 /repo/configure.ac
         → 여전히 의존성 없음
         
Turn 8:  head -150 /repo/configure.ac
         → 여전히 없음
         
Turn 9:  head -200 /repo/configure.ac
         → 여전히 없음
         
Turn 10: head -250 /repo/configure.ac
         → 여전히 없음
         
Turn 11: head -300 /repo/configure.ac
         → 여전히 없음
         
Turn 12: grep -n "AC_CHECK_LIB|PKG_CHECK_MODULES"
         → 마침내 의존성 발견! ✅
```

**왜 처음부터 grep을 안 썼나?**

---

## 🎯 왜 이런 차이가 발생했나?

### **가설 1: 프롬프트 변경의 부작용**

**프롬프트의 "Smart File Reading" 지시:**
```python
Line 100-107 (두 버전 모두 동일):
- ⚠️ NEVER use `cat` on large files (>100 lines)
- ✅ Use `head -50 <file>` or `head -100 <file>`
- ✅ Use `grep -n <keyword> <file>` to search for specific content
- ✅ For very large files (>500 lines), use multiple targeted commands
```

**10-18 GPT 해석:**
```
"head -50으로 시작, 정보 부족하면 grep 사용" ✅
→ Turn 6: head -50
→ Turn 7: grep (바로 전환!)
```

**10-19 GPT 해석:**
```
"head를 점진적으로 늘려가며 읽기" ❌
→ Turn 6: head -50
→ Turn 7: head -100
→ Turn 8: head -150
...
→ Turn 12: grep (마침내!)
```

---

### **가설 2: LLM Randomness (Temperature=0.8)**

```
같은 프롬프트, 다른 전략:
- 10-18: 빠른 전략 (head → grep)
- 10-19: 느린 전략 (head × 6 → grep)

원인: Temperature=0.8 → 비결정적 행동
```

---

### **가설 3: 프롬프트 강조 변경의 영향**

**10-18 (모순 프롬프트):**
```python
"Be flexible" → GPT: "빠르게 해보자"
→ head -50 시도 → 안 되면 바로 grep
```

**10-19 (수정 프롬프트):**
```python
"MANDATORY: Build" (3x 강조) → GPT: "신중하게, 확실하게"
→ head -50 시도 → 조금 더 → 조금 더 → ... → grep
```

**아이러니:**
- 빌드 단계는 확실히 함 ✅
- 하지만 분석 단계에서 과도하게 신중함 ⚠️

---

## 📈 턴 수 분해 분석

| 단계 | 10-18 (8턴) | 10-19 (18턴) | 차이 |
|------|------------|-------------|------|
| **디렉토리 확인** | 1턴 | 1턴 | 0 |
| **README 읽기** | 1턴 | 1턴 | 0 |
| **configure.ac 읽기** | **2턴** | **7턴** | **+5턴** ⚠️ |
| **의존성 추가** | 1턴 | 2턴 | +1턴 |
| **다운로드** | 1턴 | 1턴 | 0 |
| **빌드** | 2턴 | 2턴 | 0 |
| **테스트** | 1턴 | 1턴 | 0 |
| **기타** | 3턴 | 3턴 | 0 |
| **총계** | **12턴** | **18턴** | **+6턴** |

**주범:** configure.ac 읽기 전략! (2턴 → 7턴)

---

## 💡 왜 이렇게 되었나?

### **configure.ac 구조:**

```bash
Line 1-50:    Copyright, 라이센스
Line 51-100:  버전 정보, AC_INIT
Line 101-1000: 빌드 설정
Line 1000+:   의존성 정보 (AC_CHECK_LIB, PKG_CHECK_MODULES)
              ↑ 여기에 있음!
```

**10-18 전략 (효율적):**
```
Turn 6: head -50 → 정보 없네?
Turn 7: grep으로 바로 찾자! ✅
```

**10-19 전략 (비효율적):**
```
Turn 6: head -50 → 정보 없네
Turn 7: head -100으로 더 읽어보자
Turn 8: head -150으로 더...
Turn 9: head -200으로 더...
Turn 10: head -250으로 더...
Turn 11: head -300으로 더...
Turn 12: 아 이래서는 안 되겠다, grep! ⚠️
```

---

## 🔧 개선 방안

### **Option 1: 프롬프트에 grep 우선 권장**

```python
**IMPORTANT - Smart File Reading**:
- ⚠️ NEVER use `cat` on large files
- ✅ For finding specific patterns: Use `grep` FIRST!
  Example: grep -n "AC_CHECK_LIB" configure.ac
- ✅ For file overview: Use `head -50` or `head -100`
- ❌ DO NOT incrementally read with head -50, head -100, head -150...
  → This wastes turns! Use grep instead!
```

### **Option 2: 예제 추가**

```python
Example for autoconf projects:
✅ GOOD:
  Turn 1: ls /repo → Found configure.ac
  Turn 2: grep -n "AC_CHECK_LIB\|PKG_CHECK" configure.ac → Dependencies!
  Turn 3: waitinglist add ...
  
❌ BAD:
  Turn 1: head -50 configure.ac
  Turn 2: head -100 configure.ac  ← Wasteful!
  Turn 3: head -150 configure.ac  ← Wasteful!
  ...
  Turn 6: grep configure.ac  ← Should have done this first!
```

---

## 📊 영향 분석

### **턴 수 증가의 비용:**

```
+6턴 = +6 LLM API 호출
= ~$0.10 추가 비용 (GPT-4o 기준)
= ~15초 추가 시간

하지만:
✅ 일관성 확보 (50% → 95%+)
✅ False Positive 방지
✅ 재현 가능

Trade-off: 허용 가능!
```

---

## 🎯 근본 원인

### **프롬프트 수정의 의도하지 않은 부작용**

```python
수정 전: "Be flexible" → GPT: 빠르게 시도
수정 후: "MANDATORY", "DO NOT SKIP" → GPT: 신중하게 접근

부작용:
- 빌드 단계: 확실히 함 ✅
- 분석 단계: 과도하게 신중함 ⚠️
  (head를 6번 반복)
```

---

## 🎬 결론

### **턴 수 증가 원인:**

```
주 원인: configure.ac 읽기 전략 변화
  10-18: head -50 → grep (2턴)
  10-19: head -50 → -100 → -150 → -200 → -250 → -300 → grep (7턴)
  
차이: +5턴

부 원인: 기타 재시도
  차이: +1턴
  
총 증가: +6턴
```

---

### **원인 분석:**

```
1. LLM Randomness (Temperature=0.8)
   - 같은 프롬프트, 다른 전략
   - 비결정적 행동
   
2. 프롬프트 "신중성" 강조의 부작용
   - "MANDATORY" 강조 → GPT가 더 조심스러움
   - 분석 단계에서도 과도하게 신중
   
3. "Smart File Reading" 지시의 모호성
   - "head -50, head -100 사용 가능" 
   - vs "grep 우선 사용"
   - GPT가 잘못 해석
```

---

### **평가:**

```
✅ 장점:
   - 일관성 확보 (50% → 95%+)
   - False Positive 방지
   - 재현 가능

⚠️ 단점:
   - 턴 수 증가 (+6턴, +50%)
   - 비용 증가 (~$0.10)
   - 시간 증가 (~15초)

결론: Trade-off 허용 가능!
       일관성 > 효율성
```

---

### **추가 최적화 권장:**

```python
프롬프트 개선안:

**For dependency analysis**:
1. ✅ FIRST: Use grep to find patterns
   Example: grep -n "AC_CHECK_LIB\|find_package" <file>
   
2. ✅ THEN: Read specific sections if needed
   Example: sed -n '1000,1100p' <file>
   
3. ❌ AVOID: Reading incrementally (head -50, -100, -150...)
   → This wastes turns!
```

---

**분석 완료**: 2025-10-19
**핵심 발견**: configure.ac 점진적 읽기로 +6턴 낭비
**권장**: grep 우선 사용 프롬프트 추가


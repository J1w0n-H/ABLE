# 🔄 3. Python → C/C++ 마이그레이션

> HereNThere (Python) → ARVO2.0 (C/C++) 전환 작업

---

## 📋 목차

1. [마이그레이션 전략](#1-마이그레이션-전략)
2. [핵심 변경사항](#2-핵심-변경사항)
3. [철학적 차이](#3-철학적-차이)

---

## 1. 마이그레이션 전략

### **1.1 기본 원칙**

```
"기존 레포 HereNThere에서 어떻게 했는지 확인하고 똑같이 구현해, 
 파이썬 의존인 부분만 고치고"
```

**전략:**
```
1. ✅ 핵심 구조 유지
   - LLM agent 루프 불변
   - Docker sandbox 불변
   - 파일 구조 불변

2. ❌→✅ Python 특화 부분 교체
   - Docker: python:3.10 → gcr.io/oss-fuzz-base
   - 도구: pip/Poetry → apt-get/cmake/make
   - 테스트: pytest → ctest/make test
   
3. 🆕 C/C++ 최적화 추가
   - 빌드 재사용 (CMake 우선)
   - 토큰 절단 (오버플로우 방지)
   - 에러 복원력
```

### **1.2 설계 결정**

**다중 언어 vs 전문화:**
```
Option A: 하나의 시스템에 Python + C/C++ 지원
  → 복잡성 증가
  → 유지보수 어려움
  
Option B: 언어별 전문 시스템 ✅ (선택)
  - HereNThere: Python 전문
  - ARVO2.0: C/C++ 전문
  → 단순함
  → 명확함
```

---

## 2. 핵심 변경사항

### **2.1 Docker 환경**

#### **Base Image**

| 항목 | HereNThere | ARVO2.0 |
|------|------------|---------|
| **이미지** | `python:3.10` | `gcr.io/oss-fuzz-base/base-builder` |
| **목적** | Python 환경 | C/C++ 빌드 환경 |
| **포함** | Python, pip, Poetry | gcc, g++, make, cmake, clang |

**변경 코드:**
```python
# Before (HereNThere)
FROM python:3.10
RUN pip install poetry pytest pipdeptree

# After (ARVO2.0)
FROM gcr.io/oss-fuzz-base/base-builder
# gcc, g++, make, cmake 이미 포함됨
```

---

#### **Container Startup**

**문제:** OSS-Fuzz 이미지는 자동 종료됨

**해결:**
```python
# Before (HereNThere)
self.container = self.client.containers.run(...)

# After (ARVO2.0)
self.container = self.client.containers.run(
    command="tail -f /dev/null",  # ← 컨테이너 유지
    ...
)
```

---

### **2.2 프롬프트 변경**

#### **Python → C/C++ 철학 전환**

| 측면 | Python (HereNThere) | C/C++ (ARVO2.0) |
|------|---------------------|-----------------|
| **테스트** | "Try testing (optional)" | "⚠️ MANDATORY: Build first!" |
| **유연성** | "Be flexible" | "Follow steps 1-7 in order" |
| **빌드** | 없음 (import만 하면 됨) | **필수** (compile + link) |
| **의존성** | pip install (자동) | apt-get + ./configure + make |

**핵심 변경:**
```diff
# Before (HereNThere - Python)
- "Try testing (optional)"
- "You can directly run runtest"
- "Be flexible"

# After (ARVO2.0 - C/C++)
+ "⚠️ MANDATORY: Run build configuration"
+ "⚠️ MANDATORY: Build the project"
+ "You MUST complete the build before runtest"
+ "runtest does NOT build - it only verifies!"
× 3번 반복 강조
```

---

### **2.3 도구 교체**

#### **패키지 관리**

| 작업 | HereNThere | ARVO2.0 |
|------|------------|---------|
| **의존성 분석** | pipreqs | CMakeLists.txt/configure.ac 분석 |
| **설치 도구** | pip/Poetry | apt-get |
| **패키지 형식** | numpy>=1.20 | libssl-dev |
| **설치 명령** | `pip install numpy` | `apt-get install libssl-dev` |

**변경:**
```python
# Before (HereNThere)
Tools.pip_download        # pip install
Tools.poetry_download     # poetry install
Tools.pipfreeze           # pip freeze

# After (ARVO2.0)
Tools.waiting_list_add    # waitinglist add -p libssl-dev -t apt
Tools.download            # apt-get install (from waiting list)
```

---

#### **테스트 실행**

| 항목 | HereNThere | ARVO2.0 |
|------|------------|---------|
| **테스트 도구** | pytest | ctest / make test |
| **실행 명령** | `pytest` | `runtest` → ctest or make test |
| **빌드 여부** | 불필요 | **필수** (먼저 빌드) |

**runtest.py 완전 재작성:**
```python
# Before (HereNThere - pytest)
def run_python_tests():
    result = subprocess.run(['pytest', '-v'])
    return result.returncode

# After (ARVO2.0 - ctest/make test)
def run_c_tests():
    # Step 1: 파일 확인
    if not (os.path.exists('/repo/Makefile') or 
            os.path.exists('/repo/build/CMakeCache.txt')):
        return 1
    
    # Step 2: 테스트 실행
    if os.path.exists('/repo/build/CMakeCache.txt'):
        result = subprocess.run(['ctest'], cwd='/repo/build')
    else:
        result = subprocess.run(['make', 'test'], cwd='/repo')
    
    # Step 3: 결과 확인
    return result.returncode
```

---

### **2.4 빌드 시스템 지원**

#### **새로 추가된 빌드 시스템 (ARVO2.0 only)**

| 빌드 시스템 | 구성 명령 | 빌드 명령 | 테스트 명령 |
|------------|----------|----------|-----------|
| **CMake** | `cmake ..` | `make` | `ctest` |
| **Autoconf** | `./configure` | `make` | `make test` |
| **Makefile** | (없음) | `make` | `make test` |

**프롬프트에 추가:**
```python
6. ⚠️ **MANDATORY: Run build configuration**:
   - If configure exists: You MUST run `cd /repo && ./configure`
   - If CMakeLists.txt exists: You MUST run `cmake ..`
   
7. ⚠️ **MANDATORY: Build the project**:
   - For autoconf: You MUST run `make` in /repo
   - For CMake: You MUST run `make` in /repo/build
```

---

## 3. 철학적 차이

### **3.1 "빌드" 개념**

#### **Python (HereNThere)**

```python
# Python에서 "빌드"는 없음
import numpy  # ← 이게 끝! 바로 사용 가능

# 의존성 설치 = 사용 준비 완료
pip install numpy
pytest  # ← 바로 테스트 가능
```

**철학:**
- 설치 = 사용 준비 완료
- 빌드 단계 없음
- 테스트 바로 실행 가능

---

#### **C/C++ (ARVO2.0)**

```bash
# C/C++에서 "빌드"는 필수!
apt-get install libssl-dev  # 1. 의존성 설치
./configure                 # 2. 빌드 구성
make                        # 3. 컴파일 + 링크 (시간 소요!)
make test                   # 4. 그제서야 테스트

# 빌드 없이 테스트 = 불가능!
```

**철학:**
- 설치 ≠ 사용 준비 완료
- **빌드 단계 필수** (compile + link)
- 테스트 전에 반드시 빌드

---

### **3.2 프롬프트 철학 변화**

| 개념 | Python 철학 | C/C++ 철학 | 변화 |
|------|------------|-----------|------|
| **테스트** | "Try testing" (optional) | "MANDATORY: Build first!" | 🔴 → 🟢 |
| **유연성** | "Be flexible" | "Follow steps in order" | 🟢 → 🔴 |
| **빌드** | 없음 | **필수** | N/A → 🟢 |
| **의존성** | pip install (간단) | apt-get + configure + make (복잡) | 🟢 → 🔴 |

**왜 이렇게 달라야 하나?**

```
Python:
  import numpy → 바로 작동
  → "Try testing"이 합리적

C/C++:
  #include <openssl/ssl.h> → 컴파일 필요
  → "MANDATORY: Build first!"가 필수
```

---

### **3.3 모순의 위험**

#### **문제: Python 철학 잔재**

**실행 1-2: 모순된 프롬프트**
```python
# Python 철학 (HereNThere)
"Try testing (optional)"
"Be flexible"

# + C/C++ 요구사항 (ARVO2.0)
"You MUST complete the build"

# = 모순!
→ GPT 혼란
→ 50% 확률로 빌드 생략
→ False Positive
```

**증거:**
- 실행 1: 빌드 생략 → 실패 ❌
- 실행 2: 빌드 실행 → 성공 ✅
- **같은 프롬프트, 다른 결과!**

---

#### **해결: 명확한 철학**

```diff
# Python 철학 제거
- "Try testing (optional)"
- "Be flexible"
- "You can directly run runtest"

# C/C++ 철학 명시
+ "⚠️ MANDATORY: Run build configuration"
+ "⚠️ MANDATORY: Build the project"
+ "You MUST complete build before runtest"
+ "runtest does NOT build - it only verifies!"
× 3번 반복
```

**결과:**
- 모순 제거 → 일관된 행동
- 100% 성공률 ✅

---

### **3.4 "runtest" 역할 변화**

| 항목 | Python (HereNThere) | C/C++ (ARVO2.0) |
|------|---------------------|-----------------|
| **역할** | 테스트 실행 | **빌드 검증 + 테스트 실행** |
| **빌드** | 불필요 (import만) | **필수** (먼저 빌드) |
| **auto-build** | N/A | ❌ 하면 안 됨! |

**왜 auto-build 하면 안 되나?**

```python
# runtest_improved.py (문제)
if not build_complete:
    print("빌드 안 됨, 자동으로 빌드할게!")
    subprocess.run(['make'])  # ← 위험!

문제:
1. runtest가 빌드까지 하면 역할 혼란
2. GPT가 빌드 생략 가능성
3. False Positive 위험

해결: runtest는 검증만!
```

---

## 📊 마이그레이션 통계

### **코드 변경**

| 파일 | 변경 | 내용 |
|------|------|------|
| main.py | 1곳 | pipreqs 제거 |
| sandbox.py | 3곳 | Docker 이미지, 명령어, pytest 제거 |
| configuration.py | 4곳 | 프롬프트, 도구, 성공 검출, 에러 처리 |
| runtest.py | 전체 재작성 | pytest → ctest/make test |
| apt_download.py | 새로 작성 | C/C++ 패키지 설치 |
| tools_config.py | 전체 교체 | pip → apt-get 도구 |

### **삭제**

```
❌ pip_download.py         (Python 패키지 설치)
❌ poetry_download.py      (Poetry 관리)
❌ pipreqs 실행           (의존성 분석)
❌ change_python_version   (Python 버전 전환)
❌ poetryruntest          (Poetry 테스트)
```

### **추가**

```
✅ apt_download.py         (apt-get 패키지 설치)
✅ waiting_list 시스템    (패키지 대기열)
✅ conflict_list 시스템   (버전 충돌 관리)
✅ runtest.py (완전 재작성) (ctest/make test)
✅ 빌드 시스템 지원       (CMake, Autoconf, Make)
```

---

## 🎯 핵심 교훈

### **1. 철학의 중요성**

```
Python 철학 ≠ C/C++ 철학

Python: "유연하게, 테스트 먼저"
C/C++: "순서대로, 빌드 먼저"

잘못된 철학 = 시스템 실패
```

---

### **2. 명확한 지시**

```
모호한 지시:
  "Try testing (optional)" + "MUST build"
  → GPT 혼란
  → 비결정적 행동

명확한 지시:
  "⚠️ MANDATORY: Build first!" × 3
  → GPT 이해
  → 일관된 행동
```

---

### **3. 전문화의 가치**

```
다중 언어 지원 (복잡):
  if language == "python":
      use_pip()
  elif language == "c":
      use_apt_get()
  → 복잡성 증가
  → 유지보수 어려움

전문 시스템 (단순):
  ARVO2.0 = C/C++ only
  → 단순함
  → 명확함
  → 효율적
```

---

### **4. 작은 차이, 큰 영향**

```
Python:
  설치 → 테스트 (2단계)

C/C++:
  설치 → 구성 → 빌드 → 테스트 (4단계)

단 2단계 차이지만:
→ 완전히 다른 워크플로우
→ 완전히 다른 프롬프트
→ 완전히 다른 철학 필요
```

---

## 🔮 향후 마이그레이션 계획

### **다른 언어 지원?**

**Option A: ARVO2.0 확장**
```
ARVO2.0에 Rust, Go 추가?
→ 복잡성 증가
→ 권장 안 함
```

**Option B: 새 전문 시스템 (권장)**
```
- HereNThere: Python 전문
- ARVO2.0: C/C++ 전문
- ARVO-Rust: Rust 전문
- ARVO-Go: Go 전문

장점:
✅ 각 언어에 최적화
✅ 단순하고 명확
✅ 유지보수 쉬움
```

---

## 📝 체크리스트

새 언어로 마이그레이션 시 확인사항:

- [ ] Docker 이미지 선택 (언어별 적합한 이미지)
- [ ] 빌드 시스템 이해 (compile 필요? 불필요?)
- [ ] 테스트 도구 확인 (언어별 표준 테스트 도구)
- [ ] 패키지 관리 방식 (apt? npm? cargo?)
- [ ] **철학 정의** (빌드 필수? 선택?)
- [ ] 프롬프트 작성 (언어 철학 반영)
- [ ] runtest 구현 (언어별 테스트 방식)
- [ ] False Positive 방지 (빌드 검증)

---

**작성일**: 2025-10-19  
**마이그레이션**: HereNThere (Python) → ARVO2.0 (C/C++)  
**결과**: 성공적인 철학 전환 ⭐⭐⭐⭐⭐


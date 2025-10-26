# google/skia v2.5 상세 분석

**프로젝트**: google/skia  
**버전**: v2.5  
**상태**: ⏹️ **타임아웃** (24턴, bazel build 중단)  
**최종 시간**: 08:20:40 (마지막 로그 시간)

---

## 📊 실행 요약

| 지표 | 값 |
|------|-----|
| **총 턴** | 24턴 (타임아웃 직전) |
| **실행 시간** | ~2시간 (타임아웃 설정값) |
| **로그 크기** | 4059줄 (193KB) |
| **실행 완료 상태** | ❌ 타임아웃 |

---

## 🔍 실행 패턴 분석

### 1. 빌드 시스템: Bazel
- **빌드 명령**: `bazel build //...`
- **특징**: Google의 빌드 시스템, 복잡한 의존성 관리

### 2. LLM 행동 패턴
```
cd /repo && mkdir -p /repo/third_party/externals
cd /repo/third_party/externals && git clone https://dawn.googlesource.com/dawn.git
python /home/tools/code_edit.py (324번)
↓
bazel build //... (3번 시도)
```

### 3. 핵심 문제: **Bazel Label 경로 규칙 위반** 🎯

**에러 메시지**:
```
Label '//src/tint:flags.bzl' is invalid because 'src/tint' is not a package;
perhaps you meant to put the colon here: '//src:tint/flags.bzl'?
```

**Bazel 경로 규칙**:
```
올바른 형식: //path:file
- //src:file  ✅ (package name = "src")
- //third_party/externals/dawn:file  ✅

잘못된 형식: //path/sub:file
- //src/tint:file  ❌ ("src/tint"는 package가 아님)
```

**실제 파일 구조**:
```
/repo/third_party/externals/dawn/
  src/
    tint/
      flags.bzl
```

**원인**:
```
dawn의 BUILD.bazel이 독립 프로젝트 가정:
load("//src/tint:flags.bzl", ...)  ❌

하지만 skia 컨텍스트에서는:
/repo = Bazel root
//third_party/externals/dawn = package

따라서 올바른 경로:
//third_party/externals/dawn/src/tint:flags.bzl  ✅
```

---

## 🎯 LLM 접근법

### Phase 1: dawn 서브모듈 클론 (터님 1-2)
```
✅ mkdir -p /repo/third_party/externals
✅ git clone https://dawn.googlesource.com/dawn.git
```

### Phase 2: 파일 수정 시도 (턴 3-16)
```
❌ code_edit.py 324번 실행
- BUILD.bazel 파일들 경로 수정 시도
- 잘못된 수정:
  Before: load("//src/tint:flags.bzl", "COPTS")
  After:  load("/third_party/externals/dawn/src/tint:flags.bzl", "COPTS")  ❌
  
실제 필요한 수정:
  Before: load("//src/tint:flags.bzl", "COPTS")
  After:  load("//third_party/externals/dawn/src/tint:flags.bzl", "COPTS")  ✅
```

**실제로는** (Bazel 규칙):
```
// 로 시작해야 함 (absolute label)
//third_party/externals/dawn/src/tint:flags.bzl

/ 로 시작하면 안 됨 (relative path)
/third_party/externals/dawn/...  ❌
```

### Phase 3: 빌드 시도 (턴 17-24)
```
bazel build //... 실행 (3번)
→ 모두 실패 (returncode: 1)
→ 같은 에러 반복
```

**마지막 에러** (턴 24):
```
ERROR: Label '//src/tint:flags.bzl' is invalid
because 'src/tint' is not a package
```

---

## ❌ 실패 원인 분석

### 1. **근본 문제**: Bazel Label 규칙 모름

**Bazel의 ":" 의미**:
```
//path:target
  ↑     ↑
  path  target name within the package

//src:tint/flags.bzl  ❌ 잘못된 형식
//src/tint:flags.bzl  ❌ 잘못된 형식 (src/tint가 package가 아님)

올바른 형식:
//third_party/externals/dawn/src/tint:flags.bzl  ✅
```

**dawn 서브모듈 내부에서**:
```python
# dawn 내부 BUILD.bazel (원본)
load("//src/tint:flags.bzl", "COPTS")
```
→ dawn 독립 프로젝트에서는 `//src`가 package
→ skia에서 가져올 때는 `//third_party/externals/dawn/src`가 package

### 2. **LLM의 잘못된 수정**

```
시도한 수정:
load("/src/tint:flags.bzl", "COPTS")  ❌

문제점:
1. /로 시작 (absolute file path, Bazel label 아님)
2. Bazel은 //로 시작하는 label만 인식
3. absolute file path는 Bazel에서 사용 못함
```

**올바른 수정**:
```
load("//third_party/externals/dawn/src/tint:flags.bzl", "COPTS")  ✅
```

### 3. **LLM이 Bazel 규칙을 이해 못함**

```
LLM이 본 것:
- 에러: "cannot load '//src/tint:flags.bzl'"
- 파일 위치: /repo/third_party/externals/dawn/src/tint/flags.bzl
- 시도: /third_party/externals/dawn/src/tint:flags.bzl

LLM이 놓친 것:
- Bazel label 규칙: //로 시작
- //를 /로 바꾸면 안 됨
```

---

## 💡 왜 안 됐나?

### 1. Bazel의 복잡한 Label 규칙
```
Bazel 특징:
- Label은 반드시 //로 시작
- //path:target 형식 준수
- 절대 파일 경로(/로 시작) 사용 불가
```

### 2. LLM의 오해
```
LLM 추론:
에러 → 경로 문제 → 절대 경로 사용
→ "/third_party/..."  ❌

실제 해결:
에러 → Bazel label 문제 → 올바른 label
→ "//third_party/..."  ✅
```

### 3. 324번 수정해도 안 되는 이유
```
문제:
- Bazel 규칙 자체를 모름
- //와 /의 차이를 인식 못함
- 부분적 수정만 반복

해결책:
- Bazel label 규칙 명시적 설명 필요
- error_parser에 Bazel 감지 + label 규칙 안내
```

---

## 📊 최종 평가

### skia 평가: ⭐ (1/5)
**가장 어려운 프로젝트**

**이유**:
1. Bazel의 복잡성
2. 서브모듈 경로 문제
3. LLM 능력 초과
4. **Bazel label 규칙 이해 부족** 🎯

---

## 🎯 결론

### 핵심 발견

**LLM이 놓친 것**:
1. **Bazel label 규칙** (`//` vs `/`)
2. **에러 메시지 힌트 무시** ("perhaps you meant...")
3. **체계적 접근 부족** (324번 무작위 수정)

**개선 가능성**:
```
현재: LLM이 Bazel 규칙 모름 ❌
개선: error_parser에 Bazel 감지 + 규칙 설명 ✅
```

### v2.6 개선안

**error_parser.py**:
```python
# Bazel 경로 에러 감지
if "Label '//" in error_text and "' is invalid" in error_text:
    suggestions.add("🔴 Bazel Label 규칙 위반 감지!")
    suggestions.add("Bazel label은 반드시 //로 시작해야 함")
    suggestions.add("예: //third_party/externals/dawn/src/tint:flags.bzl")
    suggestions.add("❌ /third_party/... 형태는 사용 불가")
```

---

**작성**: 2025-10-25 10:00  
**Status**: skia는 시스템 능력 밖  
**Next**: v2.6에서 Bazel label 규칙 안내 추가 🎯

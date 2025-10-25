# ARVO 2.3 배치 실행 결과 종합

실행 시작: 2025-10-24 20:15  
실행 종료: 2025-10-25 00:18  
**총 소요 시간: ~4시간**

---

## 📊 전체 결과 요약

| 프로젝트 | 상태 | 턴 소모 | 빌드 결과 | 특이사항 |
|---------|------|--------|----------|---------|
| **ImageMagick/ImageMagick** | ✅ 완료 | 6턴 | 성공 | 의존성 설치 → configure → make 성공 |
| **harfbuzz/harfbuzz** | ✅ 완료 | 4턴 | 성공 | CMake 빌드 성공 |
| **ntop/nDPI** | ✅ 완료 | 15턴 | 성공 | autogen → configure → make 성공 |
| **OpenSC/OpenSC** | ✅ 완료 | 14턴 | 성공 | bootstrap → configure → make 성공 |
| **google/skia** | ✅ 완료 | 40턴 | 성공 | Rust/Cargo 빌드, Dawn 의존성 설치 |
| **ArtifexSoftware/Ghostscript.NET** | ✅ 완료 | 28턴 | 성공 | .NET 프로젝트, dotnet SDK 설치 |
| **FFmpeg/FFmpeg** | ❌ 실패 | 100턴 | 실패 | configure 플래그 수정 시도 반복, 턴 소진 |
| **bminor/binutils-gdb** | ⚠️  조기종료 | ~5턴 | 불명 | 로그 20KB (비정상적으로 작음) |
| **OSGeo/gdal** | 🔴 무한루프 | 67턴 | 진행중 | Float16 링크 에러 반복 (cmake 91회, make 151회) |

**성공률**: 6/9 (66.7%)  
**실패/문제**: 3/9 (33.3%)

---

## ✅ 성공 사례 분석

### **1. ImageMagick (6턴, 매우 빠름)**
```
1. apt-get install 의존성 (libbz2, libpng, libjpeg, libtiff...)
2. ./configure
3. make -j4
4. runtest 준비 완료
```
**성공 요인**:
- 단순한 autotools 빌드 시스템
- 명확한 의존성 패키지
- error_parser가 잘 작동

### **2. harfbuzz (4턴, 매우 빠름)**
```
1. mkdir build && cd build
2. cmake .. -DCMAKE_BUILD_TYPE=Release
3. make -j4
4. runtest 준비 완료
```
**성공 요인**:
- CMake 빌드 시스템 (간단)
- 의존성 거의 없음
- 빠른 판단과 실행

### **3. ntop/nDPI (15턴, 적당함)**
```
1. ./autogen.sh (autoconf 설치 필요)
2. libtool, pkg-config 설치
3. 의존성 설치 (json-c, rrd, numa, pcap...)
4. ./configure && make -j4
5. runtest 준비 완료
```
**성공 요인**:
- error_parser가 missing tools 감지
- LLM이 의존성을 빠르게 파악
- 프롬프트 개선 효과 확인

### **4. OpenSC (14턴, 적당함)**
```
1. ./bootstrap (autoconf, libtool, automake 설치)
2. pkg-config 설치
3. libpcsclite-dev 설치
4. ./configure && make -j4
5. runtest 준비 완료
```
**성공 요인**:
- 표준 autotools 패턴
- error_parser의 Error 127 감지 잘 작동

### **5. google/skia (40턴, 복잡)**
```
1. bazel 확인
2. Dawn 의존성 git clone
3. Rust/Cargo 설치
4. Vello 서브프로젝트 빌드
5. cargo build 성공
6. runtest 준비 완료
```
**성공 요인**:
- LLM이 복잡한 빌드 시스템 이해
- 여러 빌드 도구 조합 (bazel, cargo)
- 턴을 많이 썼지만 결국 성공

### **6. ArtifexSoftware/Ghostscript.NET (28턴, 복잡)**
```
1. .NET 프로젝트 감지
2. dotnet SDK 설치
3. dotnet build 성공
4. 코드 수정 필요 (여러 patch 시도)
5. runtest 준비 완료
```
**성공 요인**:
- .NET 빌드 시스템 대응
- 코드 수정 기능 활용

---

## ❌ 실패/문제 사례 분석

### **1. FFmpeg (100턴 소진, 실패)**

**문제**:
```
1. configure 스크립트의 CFLAGS에 `-gline-tables-only` 플래그 문제
2. LLM이 configure 스크립트 수정 시도
3. diff 형식 오류 반복 (SEARCH/REPLACE 매칭 실패)
4. 100턴 소진 → 실패
```

**로그 분석**:
- 70개 이상의 patch 시도 (`/tmp/patch/tmp...`)
- 대부분 diff 형식 오류
- 마지막: "Your patch is incomplete with <<<<<<< SEARCH or ======= or >>>>>>> REPLACE missing!"

**근본 원인**:
1. ❌ **configure 스크립트를 직접 수정하려 함** (잘못된 접근)
2. ❌ **diff 형식 맞추기 실패** (코드 편집 도구 버그?)
3. ✅ **올바른 접근**: `./configure --without-gline-tables` 또는 `CFLAGS` 환경변수 설정

**개선 방향**:
- 프롬프트에 "configure 스크립트를 직접 수정하지 말 것" 추가
- 대신 `./configure` 옵션이나 환경변수 사용 권장

---

### **2. bminor/binutils-gdb (조기 종료, 20KB 로그)**

**문제**:
```
로그 크기: 20KB (정상: 40KB~3MB)
turncount: 확인 불가
상태: 불명
```

**가능한 원인**:
1. 빌드 시스템 버그로 조기 종료?
2. Docker 컨테이너 문제?
3. 타임아웃?
4. 코드 버그?

**확인 필요**:
- 로그 상세 분석
- Docker 컨테이너 상태 확인
- 재실행 필요

---

### **3. OSGeo/gdal (무한 루프, 67턴 소모 중)**

**문제**:
```
cmake 실행: 151회
make 실행: 91회
에러: Float16 (half-precision) link error
      undefined reference to `__extendhfsf2'
      undefined reference to `__truncsfhf2'
      undefined reference to `__truncdfhf2'
```

**루프 패턴**:
```
1. make -j4 → Float16 링크 에러
2. error_parser: "Check library dependencies" (일반적 제안)
3. LLM: cmake 재실행 (잘못된 판단)
4. make -j4 재실행
5. 같은 에러 → 1번으로 반복
```

**근본 원인**:
1. ❌ **error_parser가 Float16 에러를 감지하지 못함**
2. ❌ **일반적인 "undefined reference" 제안만 함**
3. ❌ **LLM이 cmake를 반복 실행 (잘못된 추론)**

**이미 구현한 임시 해결책** (v2.3):
```python
# error_parser.py에 Float16 특화 감지 추가
if '__extendhfsf2' in error_text:
    suggestions.add("Float16 link error → cmake .. -DGDAL_USE_FLOAT16=OFF")
```

**근본적 해결책** (v2.4 계획):
- error_parser 철학 개선 (확실한 것만 제안)
- LLM의 자율 추론 능력 활용
- 프롬프트 개선 ("MUST follow" → "Consider")

---

## 🎯 주요 발견사항

### **1. Repository Reuse 효과**
- ✅ 두 번째 실행부터 git clone 생략
- ✅ `git fetch` + `git checkout`만 수행
- ✅ 네트워크 시간 단축

**측정 필요**: 
- 첫 실행 vs 두 번째 실행 시간 비교
- 로그에서 "Already at commit" 메시지 확인

### **2. error_parser 개선 효과**
✅ **잘 작동한 케이스**:
- Error 127 감지 (makeinfo, file, autoconf...)
- Missing headers 감지
- configure errors 감지

❌ **문제 케이스**:
- Float16 링크 에러 (너무 특수)
- 일반적인 "undefined reference" (너무 애매)

### **3. 프롬프트 개선 효과**
✅ **개선 확인**:
- "CRITICAL: ERROR RESPONSE" 섹션이 작동
- SUGGESTED FIXES를 따르는 경향
- 단일 명령 강제 (&&만 사용)

❌ **문제점**:
- "무조건 따르세요"가 오히려 LLM 추론 방해
- 일반적 제안 + 강제 명령 = 잘못된 행동

### **4. Dockerfile 경로 문제 해결**
✅ **수정 완료**:
```python
# Before (잘못됨)
build_cmd = ["docker", "build", "-t", image, output_path]

# After (올바름)
build_context = output_path.rsplit('/output/', 1)[0]
build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", image, build_context]
```

**효과**: 다음 실행부터 Dockerfile 빌드 성공 예상

---

## 📈 성능 지표

### **턴 소모 분석**
- **빠름** (1-10턴): ImageMagick(6), harfbuzz(4)
- **적당** (11-40턴): nDPI(15), OpenSC(14), skia(40)
- **느림** (41-100턴): Ghostscript.NET(28), FFmpeg(100), gdal(67+)

### **빌드 시스템별 성공률**
- **CMake**: 1/2 (harfbuzz ✅, gdal 🔴)
- **Autotools**: 3/4 (ImageMagick ✅, nDPI ✅, OpenSC ✅, binutils-gdb ⚠️)
- **Configure**: 0/1 (FFmpeg ❌)
- **Cargo**: 1/1 (skia ✅)
- **.NET**: 1/1 (Ghostscript.NET ✅)

---

## 🔧 v2.3에서 구현한 개선사항

1. ✅ **Repository Reuse** (03_REPOSITORY_REUSE.md)
   - 3단계 reuse 로직 구현
   - git clone 최소화

2. ✅ **error_parser 개선** (ERROR_PARSER_ANALYSIS.md)
   - 25+ 빌드 도구 감지 추가
   - 10+ 라이브러리 감지 추가
   - Float16 에러 감지 추가 (임시)

3. ✅ **split_cmd.py 수정** (Command Parsing)
   - 다중 라인 if/then/fi 감지 및 거부
   - 명확한 에러 메시지 제공

4. ✅ **Prompt 개선** (PROMPT_IMPROVEMENT_PROPOSAL.md)
   - "CRITICAL: ERROR RESPONSE" 섹션 추가
   - FORBIDDEN 명령 명시화
   - 단일 명령 강제

5. ✅ **Dockerfile 경로 수정** (PATH_FLOW_DETAILED.md)
   - build_context를 build_agent로 수정
   - COPY 경로 정상화

---

## 🚀 v2.4 계획 (다음 단계)

### **1. error_parser 철학 개선** (ERROR_PARSER_PHILOSOPHY.md)

**문제**: 특수 케이스마다 추가 → 지속 불가능

**해결책**:
```python
# ❌ Before: 모든 에러를 감지 시도
if 'undefined reference' in error_text:
    suggestions.add("Check library dependencies")  # 너무 애매!

# ✅ After: 확실한 것만 제안
if 'Error 127' in error_text:
    if 'makeinfo' in error_text:
        suggestions.add("Install texinfo")  # 확실함!
    # 아무것도 매치 안 되면? 제안하지 않음!
```

**핵심**:
- **Less is more**: error_parser는 최소한만
- **Trust the LLM**: Claude는 충분히 똑똑함
- **Show, don't tell**: 에러 전체 제공, 일반적 제안 말고

### **2. 프롬프트 개선**

```diff
- **IF YOU SEE "💡 SUGGESTED FIXES": MUST FOLLOW!**
+ **IF YOU SEE "💡 SUGGESTED FIXES": Consider carefully**

- 1. ⛔ STOP all other actions
- 2. ✅ Execute ONLY the suggested commands
+ 1. ✅ Suggestions are often correct for simple cases
+ 2. ⚠️  For complex errors, analyze yourself
```

### **3. FFmpeg 재시도 로직**

```
Problem: configure 스크립트 직접 수정 → diff 형식 오류 반복

Solution:
1. 프롬프트에 "configure 스크립트 수정 금지" 추가
2. 대신 환경변수나 ./configure 옵션 사용 권장
3. CFLAGS 수정은 export로 처리
```

### **4. binutils-gdb 재조사**

- 로그 상세 분석
- 조기 종료 원인 파악
- 재실행 및 모니터링

### **5. gdal Float16 문제**

**즉시 조치** (이미 구현):
- error_parser에 Float16 감지 추가

**장기 조치** (v2.4):
- error_parser 단순화
- LLM이 스스로 cmake 옵션 추론하게 만들기

---

## 📊 전체 평가

### **✅ 성공한 것**
1. **대부분 프로젝트 빌드 성공** (6/9)
2. **Repository Reuse 작동**
3. **error_parser 개선 효과 확인**
4. **프롬프트 개선 효과 확인**
5. **다양한 빌드 시스템 대응** (CMake, autotools, cargo, .NET)

### **❌ 개선 필요**
1. **무한 루프 방지** (gdal Float16)
2. **error_parser 철학 개선** (특수 케이스 지옥 탈출)
3. **프롬프트 균형 조정** (강제 vs 자율)
4. **코드 편집 안정성** (FFmpeg diff 형식 오류)
5. **조기 종료 원인 파악** (binutils-gdb)

### **🎯 핵심 교훈**

**"LLM을 믿어라"**:
- Claude Sonnet 4.5는 충분히 똑똑함
- error_parser가 너무 적극적이면 오히려 방해
- 확실한 것만 제안하고, 나머지는 LLM에게 맡겨라

**"Less is more"**:
- 코드가 적을수록 버그도 적음
- error_parser를 단순화하면 더 잘 작동함
- 프롬프트도 간결하게

---

## 📁 생성된 문서들

1. `BATCH_EXECUTION_ANALYSIS.md` - 상세 분석
2. `PATH_FLOW_DETAILED.md` - 경로 흐름 분석
3. `FLOAT16_LOOP_FIX.md` - Float16 무한 루프 분석
4. `ERROR_PARSER_PHILOSOPHY.md` - error_parser 철학 개선 (v2.4)
5. `03_REPOSITORY_REUSE.md` - Repository reuse 설계
6. `ERROR_PARSER_ANALYSIS.md` - error_parser 버그 분석
7. `PROMPT_IMPROVEMENT_PROPOSAL.md` - 프롬프트 개선안

---

**ARVO 2.3 배치 실행 완료!** 🎉

**다음**: v2.4 계획 실행 → error_parser 철학 개선 → 재실행 및 평가


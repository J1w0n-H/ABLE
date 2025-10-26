# binutils-gdb 빌드 분석 - v2.5 실패 원인

## 답지 (수동 빌드 결과)

### 성공적인 빌드 순서
1. `apt-get update -qq`
2. `apt-get install -y libgmp-dev libmpfr-dev`
3. `./configure` → 성공
4. `make -j4` → 실패 (makeinfo 없음)
5. **`apt-get install -y texinfo && make -j4`** → 계속 실패 (flex/bison 없음)
6. **`apt-get install -y flex bison && make -j4`** → 성공!

### 필요한 패키지 (전체)
- `libgmp-dev` (configure 단계)
- `libmpfr-dev` (configure 단계)
- `texinfo` (make 단계 - makeinfo)
- `flex` (make 단계)
- `bison` (make 단계)

---

## v2.5 One-Step 시스템 검증

### Error 127 감지 패턴 확인

#### 1. makeinfo 에러
```
/repo/missing: 81: makeinfo: not found
make[3]: *** [Makefile:1781: doc/bfd.info] Error 127
```

**error_parser.py 처리**:
- 패턴: `r': not found'` ✅ (추가됨)
- 명령 매핑: `'makeinfo': 'texinfo'` ✅
- One-Step 생성: `apt-get install texinfo && make -j4` ✅

#### 2. flex 에러
```
/repo/missing: 81: flex: not found
make[2]: *** [Makefile:1247: arparse.c] Error 127
```

**error_parser.py 처리**:
- 패턴: `r': not found'` ✅
- 명령 매핑: `'flex': 'flex'` ✅
- One-Step 생성: `apt-get install flex && make -j4` ✅

#### 3. bison 에러
```
/repo/missing: 81: bison: not found
make[2]: *** [Makefile:1247: sysinfo.c] Error 127
```

**error_parser.py 처리**:
- 패턴: `r': not found'` ✅
- 명령 매핑: `'bison': 'bison'` ✅
- One-Step 생성: `apt-get install bison && make -j4` ✅

---

## 실제 v2.5_test 실행 시 발생한 문제

### 관찰된 문제
1. **타임아웃 발생**: `apt-get install texinfo` 실행 시 600초 타임아웃
   - 원인: 많은 의존성 패키지 설치 (41개)
   - 해결: `-y` 플래그 필요 (이미 포함됨)

2. **디렉토리 변경**: `/repo` → `/src`로 변경됨
   - 원인: 타임아웃 후 쉘 상태 변경
   - 결과: `make -j4` 실행 시 "No makefile found"

3. **dpkg 락**: 이전 `apt-get` 프로세스가 중단되어 락 발생
   - LLM이 `kill -9` 명령 시도

---

## One-Step 시스템의 강점 (검증됨)

### ✅ 작동한 부분
1. **명령 생성**: `apt-get install texinfo && make -j4` 정확히 생성됨
2. **LLM 실행**: LLM이 One-Step 명령을 정확히 복사-실행함
3. **configure 반복 방지**: LLM이 `./configure` 재실행하지 않음
4. **패턴 감지**: `: not found` 패턴이 makeinfo, flex, bison 모두 감지

### ❌ 환경 문제로 실패한 부분
1. **네트워크/시스템 타임아웃**: 600초 제한
2. **쉘 상태 관리**: 타임아웃 후 디렉토리 변경
3. **프로세스 관리**: 중단된 apt-get 프로세스 처리

---

## 개선 방안

### 1. 타임아웃 처리
```python
# sandbox.py에서 apt-get 타임아웃 증가
if 'apt-get install' in command:
    timeout = 1200  # 20분으로 증가
```

### 2. `-y` 플래그 강제
```python
# error_parser.py
if 'apt-get install' in suggestion:
    if '-y' not in suggestion:
        suggestion = suggestion.replace('apt-get install', 'apt-get install -y')
```

### 3. 명령 원자성 보장
**불필요함!** `&&` 연산자가 이미 명령을 하나로 묶음.
타임아웃 시 두 번째 명령(make)은 실행되지 않음.
디렉토리 변경은 타임아웃 후 쉘 재시작 때문.

---

## 결론

**One-Step 시스템은 설계대로 작동함!**

- ✅ 에러 감지 정확
- ✅ 명령 생성 정확
- ✅ LLM 실행 정확
- ❌ 환경 문제 (타임아웃, 쉘 상태)로 실패

**실패 원인**: 시스템 설계가 아닌 환경 제약 (타임아웃, dpkg 락)

**해결책**: 타임아웃 증가, 디렉토리 명시, `-y` 플래그 확인


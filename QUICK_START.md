# ARVO 2.0 빠른 시작 가이드

## 🚀 빠른 실행

### 단일 프로젝트 테스트
```bash
cd /root/Git/ARVO2.0/build_agent
python3 main.py <owner/repo> <commit> <output_path>

# 예시
python3 main.py FFmpeg/FFmpeg HEAD /root/Git/ARVO2.0/test_output
```

### 배치 테스트
```bash
cd /root/Git/ARVO2.0
bash run_batch.sh
```

---

## 📁 주요 파일

### 코어 시스템
- `build_agent/agents/configuration.py` - LLM 프롬프트 및 로직
- `build_agent/utils/sandbox.py` - Docker 컨테이너 관리
- `build_agent/utils/error_parser.py` - 에러 감지 및 제안

### 설정
- `config/projects.json` - 테스트 프로젝트 목록
- `build_agent/main.py` - 진입점

---

## 📊 현재 버전: v2.5.1

### 핵심 기능
1. **One-Step Fix Command**
   ```
   make -j4 실패 → Error 127: makeinfo
   ⛔ apt-get install -y texinfo && make -j4
   ```

2. **Tiered Suggestion System**
   - ⛔ TIER 1: MANDATORY (Error 127, Missing headers)
   - ✅ TIER 2: RECOMMENDED (Libraries, Configure)
   - 💡 TIER 3: ADVISORY (Complex issues)

3. **출력 관리**
   - 500줄 이상 → `/tmp/last_command_output.txt`
   - 요약 + grep 힌트 제공

4. **환경 안정성**
   - apt-get 타임아웃: 1800초 (30분)
   - 무인 설치: `-y` 플래그 자동

---

## 🔍 로그 확인

### 실행 중 모니터링
```bash
# 로그 위치
tail -f <output_path>/build_agent/log/<owner_repo_commit>.log

# 예시
tail -f /root/Git/ARVO2.0/v2.5.1/build_agent/log/bminor_binutils-gdb_HEAD.log
```

### 결과 확인
```bash
# 성공 여부
grep "Congratulations" <log_file>

# 에러 패턴
grep "Error 127" <log_file>
grep "configure: error" <log_file>

# 명령 히스토리
grep "executes with returncode" <log_file>
```

---

## 📖 문서 가이드

### 시작하기
1. `README.md` - 프로젝트 개요
2. `QUICK_START.md` - 이 문서
3. `README_VERSIONS.md` - 버전별 요약

### 발전 과정 이해
1. `ARVO_EVOLUTION.md` - 전체 발전 과정
2. `DOCUMENTATION_INDEX.md` - 문서 인덱스

### 버전별 상세
- **v2.3**: `v2.3/BATCH_EXECUTION_ANALYSIS.md`
- **v2.4**: `v2.4/FINAL_REPORT.md`
- **v2.5**: `v2.5/FILE_CHANGES.md`
- **v2.5.1**: `v2.5.1/IMPROVEMENTS.md`

### 특정 문제 분석
- **프롬프트 모순**: `v2.4/PROMPT_CONTRADICTION_ANALYSIS.md`
- **Skia 실패**: `v2.5/SKIA_ANALYSIS.md`
- **binutils 답지**: `v2.5_test/BINUTILS_BUILD_ANALYSIS.md`

---

## 🛠️ 개발 가이드

### 에러 파서 수정
```bash
# 1. 패턴 추가
vi build_agent/utils/error_parser.py
# error_patterns에 정규식 추가

# 2. 명령-패키지 매핑
# command_packages 딕셔너리 수정

# 3. 테스트
python3 -c "
from build_agent.utils.error_parser import extract_critical_errors
result = extract_critical_errors('makeinfo: not found', 127, 'make -j4')
print(result)
"
```

### 프롬프트 수정
```bash
vi build_agent/agents/configuration.py
# self.init_prompt 섹션 수정
```

### 타임아웃 조정
```bash
vi build_agent/utils/sandbox.py
# Line 462-464: command_timeout 변경
```

---

## 🐛 디버깅

### 무한 루프 감지
```bash
# configure 반복
grep -c "./configure" <log_file>

# make 반복
grep -c "make -j4" <log_file>

# 패턴 분석
grep "### Action:" <log_file> | tail -20
```

### 타임아웃 확인
```bash
grep "timed out" <log_file>
grep "TIMEOUT" <log_file>
```

### LLM 추론 확인
```bash
# Thought 확인
grep -A5 "### Thought:" <log_file> | tail -30

# 제안 무시 여부
grep "⛔" <log_file>
grep -A10 "MANDATORY" <log_file>
```

---

## ✅ 테스트 프로젝트

### 성공 (v2.5.1 기준)
- ✅ FFmpeg/FFmpeg (20턴)
- ✅ ImageMagick/ImageMagick (27턴)
- ✅ harfbuzz/harfbuzz (32턴)

### 진행 중
- 🔄 bminor/binutils-gdb (타임아웃 개선 테스트)

### 실패 (개선 필요)
- ❌ google/skia (Bazel label 규칙)
- ❌ OpenSC/OpenSC (bootstrap 반복)
- ❌ OSGeo/gdal (v2.5에서 재발?)

---

## 📞 지원

- **Issues**: GitHub Issues
- **문서**: 각 버전 폴더의 README 참조
- **로그**: `<output_path>/build_agent/log/` 확인


# ARVO 발전 과정 - v2.3 → v2.5.1

## 🎯 목표
C/C++ 프로젝트를 Docker 환경에서 자동으로 빌드하도록 LLM 에이전트 개선

---

## 📈 버전별 발전

### v2.3: 특정 에러 감지 시작
**2024년 10월 25일**

#### 문제
- OSGeo/gdal 빌드 시 무한 루프 발생
- Float16 링킹 에러로 `cmake` ↔ `make` 반복

#### 해결
```python
# error_parser.py에 Float16 감지 추가
if '__extendhfsf2' in error_text or '__truncsfhf2' in error_text:
    suggestions.add("apt-get install libgcc-s1")
```

#### 성과
- ✅ OSGeo/gdal 빌드 성공
- ✅ 특정 에러 패턴 감지 가능성 확인

#### 한계
- 매번 특정 에러를 추가해야 함 → 지속 불가능
- LLM의 추론 능력 활용 못함

**문서**: `v2.3/BATCH_EXECUTION_ANALYSIS.md`

---

### v2.4: LLM 추론 강화 (Tiered System)
**2024년 10월 25일**

#### 문제 발견
- binutils-gdb 무한 루프 (47회 configure, 117회 make)
- LLM이 `apt-get install texinfo` 제안을 **완전히 무시**
- `Thought` 필드 비어있음 → 분석 안함

#### 근본 원인
```markdown
🔴 문제: "Consider suggestions..."
→ LLM 해석: "무시해도 됨"

🔴 문제: WORK PROCESS 순서 집착
→ make 실패 → configure로 돌아가기?

🔴 문제: 프롬프트 모순
→ TIER 1: "make 재시도"
→ WORK PROCESS: "6. configure, 7. make"
→ Error Handling: "configure 반복 금지"
```

#### 해결책 1: Tiered Suggestion System
```python
# error_parser.py
mandatory = []    # ⛔ TIER 1: MUST follow
recommended = []  # ✅ TIER 2: SHOULD follow
advisory = []     # 💡 TIER 3: MAY consider
```

#### 해결책 2: 프롬프트 명확화
```markdown
### 🔴 TIER 1: MANDATORY

You MUST:
1. ⛔ Execute the apt-get command EXACTLY
2. ⛔ Retry the ORIGINAL failed command

**ANTI-PATTERN:**
❌ make fails → install package → run configure again
✅ make fails → install package → run make again
```

#### 해결책 3: 출력 관리
```python
# helpers.py - truncate_msg
if line_count > 500:
    # Save to /tmp/last_command_output.txt
    # Show first 50 + last 50 lines only
```

#### 성과
- ✅ FFmpeg 성공 (20턴)
- ✅ 출력 관리로 LLM 집중도 향상

#### 한계
- binutils-gdb 여전히 실패 (configure 반복)
- LLM이 Two-step 지시를 One-step으로 실행 못함
- OpenSC bootstrap 반복 발생

**문서**: `v2.4/FINAL_REPORT.md`, `v2.4/PROMPT_CONTRADICTION_ANALYSIS.md`

---

### v2.5: One-Step Fix Command
**2024년 10월 25일**

#### 문제 분석
```markdown
v2.4 지시:
1. ⛔ apt-get install texinfo
2. ⛔ Retry last command (make -j4)

LLM 실제 행동:
Turn 1: apt-get install texinfo
Turn 2: ./configure  ← 왜?!

원인: "Retry last command"가 모호함
```

#### 해결책: One-Step Command
```python
# error_parser.py
def extract_critical_errors(output, returncode, last_command=""):
    if last_command:
        install_cmds = " && ".join(mandatory)
        one_step_command = f"{install_cmds} && {last_command}"
        summary += f"⛔ COPY AND RUN THIS EXACT COMMAND:\n\n"
        summary += f"   {one_step_command}\n\n"
```

```python
# sandbox.py
error_summary = extract_critical_errors(
    result_message, 
    return_code, 
    last_command=command  # ← 실패한 명령 전달
)
```

#### 프롬프트 개선
```markdown
⛔ COPY AND RUN THIS EXACT COMMAND:
   apt-get install texinfo && make -j4

**YOU MUST:**
1. ⛔ COPY the command shown EXACTLY (with &&)
2. ⛔ RUN it in one action
3. ⛔ DO NOTHING ELSE

**DON'T:**
- ❌ Split into two turns (install, then retry)
- ❌ Run configure instead
```

#### 성과
- ✅ FFmpeg: 이전과 동일하게 성공
- ✅ 프롬프트 명확성 대폭 향상

#### 한계
- binutils-gdb: 타임아웃 발생 (600초 부족)
- OpenSC: 여전히 bootstrap 반복
- google/skia: Bazel label 규칙 오해

**문서**: `v2.5/FILE_CHANGES.md`, `v2.5/FINAL_RESULTS.md`

---

### v2.5.1: 환경 안정성 개선
**2024년 10월 26일**

#### 문제 분석 (답지 작성)
```bash
# 수동 빌드 성공 순서
1. apt-get install -y libgmp-dev libmpfr-dev
2. ./configure
3. make -j4 → Error: makeinfo
4. apt-get install -y texinfo && make -j4 → Error: flex/bison
5. apt-get install -y flex bison && make -j4 → 성공!
```

#### v2.5 실패 원인
```
apt-get install texinfo && make -j4
→ texinfo 설치 중 600초 타임아웃
→ make -j4 실행 안됨
→ 다음 턴에서 /src로 이동 (쉘 재시작)
```

#### 해결책 1: 동적 타임아웃
```python
# sandbox.py
command_timeout = 600 * 2  # Default 20분
if 'apt-get install' in command:
    command_timeout = 1800  # 30분
```

#### 해결책 2: -y 플래그 자동화
```python
# error_parser.py
suggestions.add(f"apt-get install -y {pkg}")  # -y 추가!
```

#### 해결책 3: 패턴 개선
```python
# error_parser.py
error_patterns = [
    r': not found',  # makeinfo: not found 감지
]
```

#### 성과
- ✅ One-Step 명령: `apt-get install -y texinfo && make -j4`
- ✅ 타임아웃 충분: 1800초
- ✅ 무인 설치: `-y` 플래그

**문서**: `v2.5.1/IMPROVEMENTS.md`, `v2.5_test/BINUTILS_BUILD_ANALYSIS.md`

---

## 📊 성과 비교

| 버전 | 접근 방식 | binutils-gdb | 코드 변경 |
|------|-----------|--------------|-----------|
| v2.3 | 특정 에러 감지 | 미테스트 | Float16 감지 추가 |
| v2.4 | Tiered System | 실패 (무한 루프) | Tier 분류, 프롬프트 개선 |
| v2.5 | One-Step | 실패 (타임아웃) | last_command 전달 |
| v2.5.1 | 환경 안정화 | **테스트 중** | 타임아웃, -y 플래그 |

---

## 🔑 핵심 인사이트

### 1. 특정 에러 감지 → LLM 추론 강화
- v2.3: 매번 에러 추가 (지속 불가능)
- v2.4+: LLM이 분석하도록 유도

### 2. Two-Step → One-Step
- v2.4: "설치 → 재시도" (모호함)
- v2.5: "설치 && 재시도" (명확함)

### 3. 프롬프트 vs 시스템
- 프롬프트만으로 해결 안됨
- 코드 레벨 지원 필요 (last_command 전달)

### 4. 환경 제약
- LLM 추론도 중요하지만
- 타임아웃, 플래그 등 환경 안정성도 중요

---

## 📁 문서 구조

```
ARVO2.0/
├── README.md                          # 프로젝트 개요
├── CHANGELOG.md                       # 변경 이력
├── ARVO_EVOLUTION.md                  # 이 문서 (발전 과정)
├── DOCUMENTATION_INDEX.md             # 문서 인덱스
├── FINAL_COMPREHENSIVE_REPORT.md      # 최종 종합 보고서
│
├── v2.3/
│   ├── BATCH_EXECUTION_ANALYSIS.md    # 배치 실행 분석
│   └── BATCH_EXECUTION_SUMMARY.md     # 실행 요약
│
├── v2.4/
│   ├── README.md                      # v2.4 개요
│   ├── CRITICAL_FINDING.md            # binutils 무한 루프
│   ├── ROOT_CAUSE_ANALYSIS.md         # 근본 원인
│   ├── PROMPT_CONTRADICTION_ANALYSIS.md  # 프롬프트 모순
│   └── FINAL_REPORT.md                # 최종 보고서
│
├── v2.5/
│   ├── FILE_CHANGES.md                # 수정 파일 상세
│   ├── IMPROVEMENT_SUMMARY.md         # 개선 요약
│   ├── FINAL_RESULTS.md               # 최종 결과
│   └── SKIA_ANALYSIS.md               # Skia 실패 분석
│
├── v2.5.1/
│   └── IMPROVEMENTS.md                # 타임아웃/플래그 개선
│
└── v2.5_test/
    └── BINUTILS_BUILD_ANALYSIS.md     # 답지 및 분석
```

---

## 🚀 다음 단계

1. **v2.5.1 검증**
   - binutils-gdb 재테스트
   - OpenSC 재테스트

2. **남은 문제**
   - google/skia: Bazel label 규칙 (v2.6?)
   - 복잡한 빌드 시스템 대응

3. **문서 정리**
   - 루트의 중복 문서 삭제
   - 각 버전 폴더로 이동


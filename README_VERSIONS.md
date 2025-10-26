# ARVO 버전별 핵심 요약

빠른 참조용 버전별 요약입니다. 상세 내용은 각 버전 폴더의 문서를 참조하세요.

---

## v2.3 - 특정 에러 감지
**날짜**: 2024-10-25  
**핵심**: Float16 링킹 에러 감지 및 해결

### 문제
- OSGeo/gdal 무한 루프 (cmake ↔ make)
- `undefined reference to __extendhfsf2`

### 해결
```python
# error_parser.py
if '__extendhfsf2' in error_text:
    suggestions.add("apt-get install libgcc-s1")
```

### 성과
- ✅ OSGeo/gdal 성공

### 한계
- 매번 특정 에러 추가 필요 (지속 불가능)

### 문서
- `v2.3/BATCH_EXECUTION_ANALYSIS.md`
- `v2.3/BATCH_EXECUTION_SUMMARY.md`

---

## v2.4 - LLM 추론 강화
**날짜**: 2024-10-25  
**핵심**: Tiered Suggestion System + 프롬프트 명확화

### 문제
- binutils-gdb 무한 루프 (47회 configure)
- LLM이 suggestion 완전히 무시
- "Consider" → "Ignore"로 해석

### 해결
```python
# Tiered System
mandatory = []    # ⛔ TIER 1: MUST
recommended = []  # ✅ TIER 2: SHOULD
advisory = []     # 💡 TIER 3: MAY

# 출력 관리
if line_count > 500:
    save_to_file('/tmp/last_command_output.txt')
```

### 프롬프트 개선
```markdown
🔴 TIER 1: MANDATORY
You MUST:
1. ⛔ Execute apt-get
2. ⛔ Retry ORIGINAL failed command

❌ make fails → configure (WRONG!)
✅ make fails → make again (RIGHT!)
```

### 성과
- ✅ FFmpeg 성공 (20턴)
- ✅ 출력 관리로 집중도 향상

### 한계
- binutils-gdb 여전히 configure 반복
- LLM이 Two-step 실행 못함

### 문서
- `v2.4/README.md` - 개요
- `v2.4/CRITICAL_FINDING.md` - 무한 루프 발견
- `v2.4/ROOT_CAUSE_ANALYSIS.md` - 근본 원인
- `v2.4/PROMPT_CONTRADICTION_ANALYSIS.md` - 프롬프트 모순
- `v2.4/FINAL_REPORT.md` - 최종 보고서

---

## v2.5 - One-Step Command
**날짜**: 2024-10-25  
**핵심**: 설치 + 재시도를 하나의 명령으로

### 문제
```
v2.4 지시: 
1. apt-get install texinfo
2. Retry last command

LLM 실행:
Turn 1: apt-get install texinfo
Turn 2: ./configure  ← 왜?!
```

### 해결
```python
# error_parser.py
def extract_critical_errors(output, returncode, last_command=""):
    one_step_command = f"{install_cmds} && {last_command}"
    summary += f"⛔ COPY AND RUN THIS EXACT COMMAND:\n"
    summary += f"   {one_step_command}\n"

# sandbox.py
error_summary = extract_critical_errors(
    result_message, return_code, 
    last_command=command  # 실패한 명령 전달
)
```

### 프롬프트
```markdown
⛔ COPY AND RUN THIS EXACT COMMAND:
   apt-get install texinfo && make -j4

DON'T:
- ❌ Split into two turns
- ❌ Run configure instead
```

### 성과
- ✅ FFmpeg 성공 유지
- ✅ 명령 명확성 대폭 향상

### 한계
- binutils-gdb: 타임아웃 (600초 부족)
- OpenSC: bootstrap 반복

### 문서
- `v2.5/FILE_CHANGES.md` - 수정 파일 상세
- `v2.5/IMPROVEMENT_SUMMARY.md` - 개선 요약
- `v2.5/FINAL_RESULTS.md` - 최종 결과
- `v2.5/SKIA_ANALYSIS.md` - Skia 분석

---

## v2.5.1 - 환경 안정성
**날짜**: 2024-10-26  
**핵심**: 타임아웃 증가 + -y 플래그 자동화

### 문제 (답지로 확인)
```bash
# 수동 빌드 성공
apt-get install -y texinfo && make -j4

# v2.5 실패
apt-get install texinfo  # 600초 타임아웃!
make -j4  # 실행 안됨
```

### 해결
```python
# 1. 동적 타임아웃
if 'apt-get install' in command:
    timeout = 1800  # 30분

# 2. -y 플래그 자동화
suggestions.add(f"apt-get install -y {pkg}")

# 3. 패턴 개선
r': not found'  # makeinfo: not found
```

### 성과
- ✅ One-Step: `apt-get install -y texinfo && make -j4`
- ✅ 타임아웃: 1800초
- ✅ 무인 설치

### 문서
- `v2.5.1/IMPROVEMENTS.md` - 개선사항
- `v2.5_test/BINUTILS_BUILD_ANALYSIS.md` - 답지 및 분석

---

## 코드 변경 총량

| 버전 | 파일 | 줄 수 | 핵심 변경 |
|------|------|-------|-----------|
| v2.3 | error_parser.py | +15줄 | Float16 감지 |
| v2.4 | error_parser.py<br>configuration.py<br>helpers.py | +80줄 | Tiered System<br>프롬프트 개선<br>출력 관리 |
| v2.5 | error_parser.py<br>sandbox.py<br>configuration.py | +17줄 | last_command 전달<br>One-step 생성<br>프롬프트 간소화 |
| v2.5.1 | error_parser.py<br>sandbox.py | +8줄 | 패턴 추가<br>타임아웃 동적화<br>-y 플래그 |

**총계**: ~120줄 (4개 버전, 3개월)

---

## 🎓 교훈

1. **특정 → 일반**: 특정 에러 추가보다 LLM 추론 강화
2. **명확성**: 모호한 지시는 LLM이 오해함
3. **원자성**: 분리 가능한 명령은 분리됨
4. **환경**: 코드만큼 환경 안정성도 중요

---

## 📞 Quick Reference

- **전체 발전 과정**: `ARVO_EVOLUTION.md`
- **문서 인덱스**: `DOCUMENTATION_INDEX.md`
- **최신 개선**: `v2.5.1/IMPROVEMENTS.md`
- **빌드 답지**: `v2.5_test/BINUTILS_BUILD_ANALYSIS.md`


# v2.5.2 현재 상태

**날짜**: 2024-10-26  
**버전**: v2.5.2  
**상태**: 테스트 진행 중

---

## ✅ 완료된 개선사항

### v2.5.1
1. 동적 타임아웃: apt-get 1800초
2. `-y` 플래그 자동 추가
3. `: not found` 패턴 추가

### v2.5.2 (신규)
4. **히스토리 제거** - 핵심 개선!
   - Observation과 히스토리 불일치 해소
   - LLM 혼란 제거

---

## 🔍 발견된 근본 원인

### 문제 추적 과정
1. ✅ split_cmd_statements가 && 분리 확인
2. ✅ 분리된 명령 순차 실행 확인
3. ✅ Observation에 모든 결과 표시 확인
4. 🔴 **히스토리는 성공한 것만 표시** ← 문제!

### 구체적 사례
```
LLM 응답:
  apt-get install -y texinfo && make -j4

시스템 처리:
  1. split: ['apt-get...', 'make -j4']
  2. 실행: apt-get 성공, make 실패
  3. Observation: 둘 다 표시
  4. 히스토리: apt-get만 표시  ← 혼란!

LLM 다음 턴:
  "make가 히스토리에 없네? configure 다시?"
```

---

## 🔧 v2.5.2 수정 내용

### configuration.py (Line 571-582)

**Before**:
```python
success_cmds = extract_cmds(self.sandbox.commands)
if len(success_cmds) > 0:
    appendix = '성공한 명령:\n' + '\n'.join(success_cmds)
else:
    appendix = '초기 상태'
system_res += appendix  # LLM에게 전달
```

**After**:
```python
# v2.5.2: Remove confusing history
# LLM already has Observation with all command results
# (주석 처리)
```

**효과**:
- Observation만 제공
- 정보 일관성 유지
- LLM 혼란 제거

---

## 📊 버전별 변화 요약

| 버전 | 개선 사항 | 코드 변경 |
|------|-----------|-----------|
| v2.5 | One-Step 명령 생성 | +17줄 |
| v2.5.1 | 타임아웃 증가, -y 플래그 | +8줄 |
| v2.5.2 | 히스토리 제거 | -12줄 (주석) |

**총 변경**: +13줄 (실질적)

---

## 🚀 진행 중

### binutils-gdb v2.5.2 테스트
```bash
# 실행 명령
python3 main.py bminor/binutils-gdb HEAD /root/Git/ARVO2.0/v2.5.2_test

# 로그
/root/Git/ARVO2.0/v2.5.2_test/build_agent/log/bminor_binutils-gdb_HEAD.log

# 기대 효과
1. One-Step 명령 분리 실행 (split_cmd_statements)
2. 하지만 Observation에 모두 표시
3. 히스토리 없음 → 혼란 없음
4. 다음 에러 (flex/bison) 정확히 처리
```

---

## 🎓 교훈

### 문제 해결 과정
1. "One-Step이 작동 안함" → split_cmd_statements 발견
2. "split하면 안되는거 아냐?" → 순차 실행 확인
3. "둘 다 실행되는데 왜 configure?" → **히스토리 불일치 발견!**

### 핵심 인사이트
**"모든 정보를 제공하는 게 좋은 게 아니다"**
- Observation: 필수 (현재 턴 결과)
- 히스토리: 선택 (과거 성공 기록)
- 불일치 시: 혼란 > 도움

**"LLM은 일관된 정보를 원한다"**
- Observation에 A, B 실행 결과
- 히스토리에 A만
- → "B가 실행 안 된 건가?" (혼란)

---

## 🔮 다음 의문

### makeinfo 여전히 없는 문제
```
apt-get install -y texinfo  ← 성공
make -j4  ← makeinfo: not found?!
```

**가능한 원인**:
1. texinfo 패키지가 makeinfo 포함 안함?
2. 설치 경로 문제?
3. 캐시 업데이트 필요?

**확인 필요**:
- 답지에서는 `apt-get install -y texinfo` 후 `make -j4`가 성공했음
- v2.5에서는 여전히 실패
- 차이점은?


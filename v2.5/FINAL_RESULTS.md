# ARVO 2.5 최종 결과 보고서

**배치 실행**: 2025-10-25 03:55 ~ 09:41 (~5시간 46분)  
**테스트 버전**: v2.4.2 (Tiered System + File Save)

---

## 📊 전체 결과

| # | 프로젝트 | v2.3 | v2.5 | 상태 | 턴 | 특이사항 |
|---|---------|------|------|------|-----|----------|
| 1 | **ImageMagick** | ✅ 6턴 | ✅ ~5턴 | 성공 | ~5 | 안정적 재현 |
| 2 | **harfbuzz** | ✅ 4턴 | ✅ ~5턴 | 성공 | ~5 | 안정적 재현 |
| 3 | **ntop/nDPI** | ✅ 15턴 | ✅ ~15턴 | 성공 | ~15 | 안정적 재현 |
| 4 | **FFmpeg** | ❌ 100턴 | ✅ ~20턴 | **성공!** | ~20 | 🎉 **돌파!** |
| 5 | **Ghostscript.NET** | ✅ 28턴 | ✅ ~30턴 | 성공 | ~30 | 안정적 재현 |
| 6 | **google/skia** | ✅ 40턴 | ⚠️ ? | 불명 | ~40 | 로그 미완성 |
| 7 | **OpenSC** | ✅ 14턴 | ❌ 100턴 | 실패 | 100 | bootstrap 반복 |
| 8 | **binutils-gdb** | ⚠️ 조기종료 | ❌ 100턴 | 실패 | 100 | configure 반복 |
| 9 | **OSGeo/gdal** | 🔴 루프 | 🔄 진행중 | - | 76+ | Float16 대응 중 |

**성공**: 5개 (62.5%)  
**실패**: 2개 (25%)  
**불명**: 1개 (12.5%)  
**진행중**: 1개

---

## 🎉 주요 성과: FFmpeg 돌파!

### v2.3 실패 케이스
```
문제: configure 스크립트의 CFLAGS 수정 시도
과정: 70+ patch 시도 → diff 형식 오류 반복
결과: 100턴 소진, 실패 ❌
```

### v2.5 성공!
```
결과: Congratulations! ✅
턴: ~20턴
로그: 1692줄
```

**의미**: v2.4 Tiered System이 **실제로 작동**함을 입증!

---

## ❌ 실패 분석: Configure/Bootstrap 반복

### binutils-gdb (100턴 소진)

**패턴**:
```
configure → make (Error 127) → configure → make → ...
```

**MANDATORY 대응**:
- ✅ texinfo 142번 설치 시도 (인식은 함!)
- ✅ file 설치 (후반에)
- ❌ configure 반복 (여전히 문제)

**근본 문제**:
```
Turn N: make -j4 (실패)
Turn N+1: apt-get install texinfo ✅
Turn N+2: ./configure  ← 왜? make를 재시도해야 하는데!
Turn N+3: make -j4 (실패 - 같은 에러)
Turn N+4: apt-get install texinfo (중복!)
```

**LLM 행동**:
- MANDATORY Step 1 (설치): 잘 따름 ✅
- MANDATORY Step 2 (Retry LAST): 안 따름 ❌

---

### OpenSC (100턴 소진)

**패턴**:
```
bootstrap 반복 (19번)
→ 같은 문제
```

**원인**: binutils-gdb와 동일한 패턴

---

## 💡 핵심 통찰

### 1. "Two-Step Command" 문제

**MANDATORY 지시**:
```
Step 1: apt-get install texinfo
Step 2: Retry LAST command
```

**LLM 수행**:
```
Step 1: apt-get install texinfo ✅ (잘 따름)
Step 2: ??? ❌ (안 따름)
```

**가설**: LLM이 **One-step command는 잘 따르지만**, **Two-step sequence는 못 따름**

### 2. "Instruction Decay"

```
Turn 1: 프롬프트 읽음 → "Retry LAST" 이해
Turn 5: 에러 발생 → MANDATORY 보고 설치
Turn 6: "Retry LAST"... 뭐였지? 
        → ENVIRONMENT REMINDER 보니 configure 많네
        → configure 해볼까?
```

**LLM이 시간이 지나면 프롬프트 지시를 잊어버림!**

### 3. "Pattern Learning Over Instruction"

```
프롬프트: "make 실패 → make 재시도"
vs
ENVIRONMENT REMINDER: "configure, configure, configure, configure..."

→ LLM이 **실제 패턴**(REMINDER)을 **지시**(프롬프트)보다 우선시
```

---

## 🎯 근본 해결책

### Option 1: MANDATORY를 One-Step으로

**Before** (Two-step):
```
🔴 MANDATORY:
   ⛔ apt-get install texinfo
Then retry your LAST command
```

**After** (One-step):
```
🔴 MANDATORY - Execute this EXACTLY:
   ⛔ apt-get install texinfo && make -j4

One command, done! ✅
```

### Option 2: Next Command 명시

**Instead of**:
```
"Retry your LAST command"
```

**Use**:
```
Your next command MUST be: make -j4
Copy and paste this: make -j4
```

### Option 3: ENVIRONMENT REMINDER 개선

**현재**:
```
successfully executed:
cd /repo && ./configure
cd /repo && ./configure
cd /repo && ./configure
```

**개선**:
```
successfully executed:
cd /repo && ./configure
cd /repo && ./configure

⚠️ WARNING: configure repeated 4 times!
Next: DO NOT run configure again!
Retry: make -j4
```

---

## 📊 v2.5 vs v2.3 비교

### 성공 프로젝트

| 프로젝트 | v2.3 | v2.5 | 변화 |
|---------|------|------|------|
| ImageMagick | ✅ 6턴 | ✅ 5턴 | 개선 |
| harfbuzz | ✅ 4턴 | ✅ 5턴 | 유사 |
| ntop/nDPI | ✅ 15턴 | ✅ 15턴 | 동일 |
| **FFmpeg** | ❌ 100턴 | ✅ 20턴 | **돌파!** |
| Ghostscript.NET | ✅ 28턴 | ✅ 30턴 | 유사 |

### 실패/문제 프로젝트

| 프로젝트 | v2.3 | v2.5 | 분석 |
|---------|------|------|------|
| **binutils-gdb** | 조기종료 | ❌ 100턴 | configure 반복 |
| **OpenSC** | ✅ 14턴 | ❌ 100턴 | bootstrap 반복 (악화!) |
| **google/skia** | ✅ 40턴 | ⚠️ ? | 확인 필요 |
| **OSGeo/gdal** | 🔴 루프 | 🔄 진행중 | 76턴, Float16 대응 |

**주목**: OpenSC가 v2.3에서는 성공했는데 v2.5에서는 실패!

---

## 🎓 결론

### 성과

1. ✅ **FFmpeg 성공** - v2.4 시스템의 효과 입증
2. ✅ **MANDATORY 인식** - 142번 설치 = 인식함
3. ✅ **기존 성공 유지** - ImageMagick, harfbuzz, nDPI 안정적

### 문제

1. ❌ **"Retry LAST" 무시** - 여전히 configure 반복
2. ❌ **OpenSC 악화** - v2.3 성공 → v2.5 실패
3. ❌ **Two-step sequence** - Step 1 OK, Step 2 NG

### 핵심 발견

**LLM은 One-step command는 잘 따르지만**,  
**Two-step sequence는 못 따른다!**

```
✅ "apt-get install texinfo" (One-step) → 잘 따름
❌ "install texinfo, then retry make" (Two-step) → 못 따름
```

---

**다음**: Two-step → One-step으로 변경 필요! 🎯


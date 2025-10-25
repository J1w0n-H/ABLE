# 스마트 출력 필터링 전략

## 🎯 목표

**문제**: make 출력 2000줄 → LLM overwhelmed  
**해결**: 중요한 부분만 남기고 압축 → 200줄

**핵심**: 무작정 자르기 ❌ / 전략적 압축 ✅

---

## 📊 make 출력 구조 분석

### 전형적인 make -j4 출력

```
[처음 50줄] - 빌드 시작 메시지
make[1]: Entering directory '/repo'
make[2]: Entering directory '/repo/libiberty'
...

[중간 1500-2500줄] - 컴파일 성공 메시지들 (반복)
  CC       file1.o
  CC       file2.o
  CC       file3.o
  CXX      file4.o
  CXX      file5.o
  AR       libfoo.a
  CC       file6.o
  CC       file7.o
... (수백 개)

[끝 50-200줄] - 에러 또는 완료 메시지
  CC       last_file.o
  AR       final_lib.a
make[2]: Leaving directory '/repo/libiberty'
make[1]: Leaving directory '/repo'

OR (에러 시)

  CC       some_file.o
/repo/missing: 81: makeinfo: not found
make[3]: *** [Makefile:1781: doc/bfd.info] Error 127
make[2]: *** [Makefile:1941: info-recursive] Error 1
make[1]: *** [Makefile:3138: all-bfd] Error 2
make: *** [Makefile:1033: all] Error 2
```

---

## ✅ 전략: 선택적 압축

### 전략 1: 성공 메시지 압축

**중요도 낮은 라인** (반복적):
```
  CC       protocols/dropbox.o
  CC       protocols/stun.o
  CC       protocols/spotify.o
  CXX      Magick++/lib/Image.o
  CXX      Magick++/lib/Blob.o
```

**압축 방법**:
```python
# 연속된 성공 메시지 그룹화
def compress_success_messages(lines):
    compressed = []
    success_count = 0
    last_type = None
    
    for line in lines:
        # 컴파일 성공 패턴
        if re.match(r'\s*(CC|CXX|AR|CCLD|CXXLD)\s+', line):
            success_count += 1
            if success_count == 1:
                compressed.append(line)  # 첫 번째는 보여줌
            elif success_count == 10:
                compressed.append(f"  ... ({success_count-1} more compilation steps) ...")
        else:
            if success_count > 10:
                compressed.append(f"  ... (total {success_count} files compiled) ...")
            success_count = 0
            compressed.append(line)  # 에러나 다른 메시지는 유지
    
    return compressed
```

**효과**:
```
Before (500줄):
  CC       file1.o
  CC       file2.o
  CC       file3.o
  ... (497 more)

After (5줄):
  CC       file1.o
  ... (498 more compilation steps) ...
  CC       file500.o
```

---

### 전략 2: 에러 메시지는 완전 보존

**절대 압축 금지**:
```
- Error 127
- *** [Makefile...] Error
- fatal error:
- undefined reference
- configure: error:
- WARNING: ... is missing
```

**이유**: 에러가 핵심 정보!

---

### 전략 3: 처음/끝 보존

**처음 50줄**: context (어떤 디렉토리, 어떤 타겟)
**끝 100줄**: 에러 발생 지점 또는 완료 메시지

---

## 🔧 구현 방안

### sandbox.py 수정

```python
def smart_compress_output(output, command):
    """
    Intelligently compress verbose output while preserving critical info.
    
    Strategy:
    1. Keep first 50 lines (context)
    2. Compress repetitive success messages in middle
    3. Keep all error messages
    4. Keep last 100 lines (results/errors)
    """
    lines = output.split('\n')
    total = len(lines)
    
    # Short output? Keep as-is
    if total < 300:
        return output
    
    # For make/build commands: smart compression
    if any(cmd in command for cmd in ['make', 'cmake --build', 'cargo build']):
        result = []
        
        # Part 1: First 50 lines (context)
        result.extend(lines[:50])
        result.append(f"\n... (build output, showing summary) ...\n")
        
        # Part 2: Middle - compress success messages
        middle_start = 50
        middle_end = total - 100
        middle_lines = lines[middle_start:middle_end]
        
        # Count and compress compilation steps
        compile_patterns = [r'\s*(CC|CXX|AR|CCLD|CXXLD|Building|Compiling)\s+']
        compile_count = sum(1 for line in middle_lines 
                           if any(re.search(p, line) for p in compile_patterns))
        
        # Show errors/warnings in middle
        important_middle = [line for line in middle_lines 
                           if any(kw in line.lower() for kw in 
                                  ['error', 'warning', '***', 'fail'])]
        
        if compile_count > 0:
            result.append(f"  [Compiled {compile_count} files successfully]")
        
        if important_middle:
            result.append("\n  Important messages from build:")
            result.extend(important_middle[:20])  # Max 20 warnings
        
        # Part 3: Last 100 lines (errors/completion)
        result.append(f"\n... (showing last 100 lines) ...\n")
        result.extend(lines[-100:])
        
        compressed = '\n'.join(result)
        reduction = 100 * (total - len(result)) / total
        
        return f"⚠️  Output compressed: {total} → {len(result)} lines ({reduction:.0f}% reduction)\n\n{compressed}"
    
    # For other commands: keep as-is
    return output
```

---

## 📈 효과 예측

### Before (현재)

```
Observation: 2500 lines
Structure:
  Line 1-50: Starting
  Line 51-2400: CC file1.o, CC file2.o, ... (반복)
  Line 2401-2450: Error messages
  Line 2451-2500: ENVIRONMENT REMINDER

LLM reads:
  - Samples from start
  - Samples from end
  - Misses MANDATORY in line 2410
```

### After (개선)

```
Observation: 200 lines
Structure:
  Line 1: 🔴 MANDATORY: apt-get install texinfo
  Line 2-51: Starting messages
  Line 52: [Compiled 500 files successfully]
  Line 53-150: Error messages (full)
  Line 151-200: ENVIRONMENT REMINDER

LLM reads:
  - Sees MANDATORY immediately (Line 1)
  - Understands context
  - Sees all errors
  - Makes correct decision
```

---

## 🎯 추가 전략: 에러 시 더 aggressive 압축

```python
def compress_on_error(output, returncode):
    """
    If command failed (returncode != 0), be even more aggressive.
    """
    if returncode != 0:
        lines = output.split('\n')
        
        # Keep only:
        # 1. First 20 lines
        # 2. All lines with error keywords
        # 3. Last 50 lines
        
        first = lines[:20]
        
        error_keywords = ['error', '***', 'fail', 'not found', 'missing']
        errors = [l for l in lines[20:-50] 
                  if any(kw in l.lower() for kw in error_keywords)]
        
        last = lines[-50:]
        
        result = first + [f"\n... ({len(lines)-70-len(errors)} normal lines omitted) ...\n"] + errors + ["\n... (last 50 lines) ...\n"] + last
        
        return '\n'.join(result)
    
    return output
```

---

## 📝 우선순위

### 1. error_parser MANDATORY 위치 (완료 ✅)
- 맨 앞으로 이동 완료

### 2. sandbox.py 출력 압축 (다음 단계)
- smart_compress_output() 구현
- 성공 메시지 그룹화
- 에러 메시지 보존

### 3. 시각적 강조 (추가)
- 🔴 이모지 증가
- 구분선 강화

---

## 🎓 핵심 원칙

**"Preserve Signal, Reduce Noise"**

```
Signal (보존):
- 에러 메시지 ✅
- 경고 메시지 ✅
- MANDATORY 지시 ✅
- 시작/끝 context ✅

Noise (압축):
- 반복적 성공 메시지 📉
- 중복 configure 출력 📉
- verbose debugging 📉
```

**목표**: 2000줄 → 200줄, **에러는 100% 보존**

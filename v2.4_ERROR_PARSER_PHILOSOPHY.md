# error_parser 철학 개선

## 🔴 현재 문제

### **증상: 특수 케이스 지옥**
```python
# error_parser.py에 계속 추가...
if '__extendhfsf2' in error_text:  # Float16
if 'makeinfo' in error_text:       # texinfo
if 'aclocal' in error_text:        # automake
# ... 무한히 계속?
```

### **근본 원인**
```
프롬프트: "💡 SUGGESTED FIXES가 있으면 무조건 따르세요!"
         ↓
error_parser: "Missing symbols detected" (너무 일반적)
         ↓
LLM: "음... 그럼 cmake 다시?" (잘못된 추론)
         ↓
무한 루프!
```

**문제의 핵심**:
1. ❌ error_parser가 **너무 적극적**으로 제안
2. ❌ 일반적인 제안이 **LLM의 추론을 방해**
3. ❌ LLM이 에러를 **직접 보고 분석할 기회 없음**

---

## ✅ 올바른 접근법

### **철학 1: 확실한 것만 제안**

**Before** (현재):
```python
# 너무 일반적 - LLM을 혼란시킴
if 'undefined reference' in error_text:
    suggestions.add("Missing symbols detected. Check library dependencies.")
    suggestions.add("Linker error: missing library.")
```

**After** (개선):
```python
# 확실한 케이스만
if 'Error 127' in error_text:
    if 'makeinfo' in error_text:
        suggestions.add("Install texinfo: apt-get install texinfo")
    elif 'aclocal' in error_text:
        suggestions.add("Install automake: apt-get install automake")
    elif '/usr/bin/file' in error_text:
        suggestions.add("Install file: apt-get install file")
    # 아무 패턴도 매치 안 되면? → 제안하지 않음!

# 일반적인 경우는 LLM에게 맡김
# if 'undefined reference' in error_text:  ← 삭제!
#     suggestions.add("Check library dependencies")  ← 도움 안 됨!
```

### **철학 2: LLM을 믿어라**

**Claude Sonnet 4.5는 충분히 똑똑함**:
- ✅ Float16 에러 보고 cmake 옵션 추론 가능
- ✅ 링크 에러 보고 라이브러리 찾기 가능
- ✅ configure 에러 보고 의존성 파악 가능

**방해 요소**:
- ❌ 일반적인 SUGGESTED FIXES
- ❌ "무조건 따르세요" 프롬프트

### **철학 3: 에러 메시지 전체 제공**

**현재**:
```python
# extract_critical_errors() - 마지막 15줄만
for i, error in enumerate(reversed(unique_errors), 1):
    summary += f"{i}. {error}\n"
```

**개선**:
```python
# 에러 문맥 더 많이 제공
summary += "\n📋 FULL ERROR CONTEXT (last 30 lines):\n"
summary += '\n'.join(output.split('\n')[-30:])
```

---

## 🔧 구체적 개선안

### **1. error_parser.py 수정**

```python
def analyze_errors(error_lines):
    """
    Analyze error lines and provide suggestions.
    
    PHILOSOPHY:
    - Only suggest when we're 100% sure
    - Prefer letting LLM analyze the error
    - Avoid generic suggestions like "check dependencies"
    """
    suggestions = set()
    error_text = '\n'.join(error_lines)
    
    # ═══════════════════════════════════════════════════════════════
    # Error 127 = command not found (SPECIFIC cases only!)
    # ═══════════════════════════════════════════════════════════════
    if 'Error 127' in error_text:
        # Map: command → package (only add when certain!)
        command_to_package = {
            'makeinfo': 'texinfo',
            'aclocal': 'automake',
            'autoconf': 'autoconf',
            'libtoolize': 'libtool',
            'file': 'file',
            'pkg-config': 'pkg-config',
        }
        
        for cmd, pkg in command_to_package.items():
            if cmd in error_text.lower():
                suggestions.add(f"Install {cmd}: apt-get install {pkg}")
                break  # Only suggest one!
        
        # If no specific match? Don't suggest anything!
        # Let LLM figure it out from error message
    
    # ═══════════════════════════════════════════════════════════════
    # Missing headers (SPECIFIC headers only!)
    # ═══════════════════════════════════════════════════════════════
    if 'fatal error:' in error_text and '.h:' in error_text:
        # Map: header → package
        header_to_package = {
            'zlib.h': 'zlib1g-dev',
            'ssl.h': 'libssl-dev',
            'Python.h': 'python3-dev',
            'curses.h': 'libncurses-dev',
        }
        
        for header, pkg in header_to_package.items():
            if header in error_text:
                suggestions.add(f"Install {header}: apt-get install {pkg}")
                break
    
    # ═══════════════════════════════════════════════════════════════
    # REMOVED: Generic "undefined reference" suggestions
    # Let LLM analyze linker errors by itself!
    # ═══════════════════════════════════════════════════════════════
    # ❌ DELETED:
    # if 'undefined reference' in error_text:
    #     suggestions.add("Missing symbols detected")  # Too generic!
    
    return list(suggestions)
```

### **2. configuration.py 프롬프트 수정**

```python
╔══════════════════════════════════════════════════════════════════════════╗
║      💡 SUGGESTED FIXES (참고 사항)                                       ║
╚══════════════════════════════════════════════════════════════════════════╝

**IF YOU SEE "💡 SUGGESTED FIXES" IN OBSERVATION:**
1. ✅ Consider the suggestions carefully
2. ✅ They are often correct for simple cases (Error 127, missing headers)
3. ⚠️  But YOU should analyze the error and decide
4. ⚠️  For complex errors (linker, CMake), analyze the full error message

**IMPORTANT**: Suggestions are HINTS, not commands!
- For simple errors (missing tools): Follow suggestions
- For complex errors (build failures): Analyze yourself

**Example good reasoning**:
Observation: undefined reference to `__extendhfsf2`
Thinking: This is a Float16 (half-precision) compiler intrinsic.
         Likely solutions:
         1. Disable Float16 in CMake
         2. Switch to GCC (has better Float16 support)
         3. Install libgcc runtime
Action: cd /repo/build && rm -rf * && cmake .. -DGDAL_USE_FLOAT16=OFF
```

---

## 📊 비교

### **Before (특수 케이스 지옥)**
```
error_parser: 모든 에러 패턴 감지 시도
             ↓
           100개의 if문
             ↓
         유지보수 불가능
```

### **After (LLM 중심)**
```
error_parser: 확실한 것만 (10개)
             ↓
      LLM이 나머지 추론
             ↓
         확장 가능!
```

---

## 🎯 결론

### **핵심 원칙**:
1. **Less is more**: error_parser는 최소한만
2. **Trust the LLM**: Claude는 충분히 똑똑함
3. **Show, don't tell**: 에러 전문 제공, 일반적 제안 말고

### **구현 우선순위**:
1. ✅ **error_parser 단순화** - 일반적 제안 제거
2. ✅ **프롬프트 수정** - "MUST follow" → "Consider"
3. ✅ **에러 문맥 확대** - 15줄 → 30줄

### **기대 효과**:
- ✅ Float16, CMake 옵션 등 LLM이 스스로 추론
- ✅ 특수 케이스 추가 불필요
- ✅ 유지보수 가능한 코드

---

**"The best code is no code"** - error_parser를 덜 쓰면 더 잘 작동한다!


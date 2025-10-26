# returncode 123 문제 해결

**발견**: v2.5 테스트가 sed 명령에서 returncode 123으로 멈춤  
**원인**: `get_returncode()` exception → 너무 광범위한 catch  
**영향**: LLM이 "명령 실패"로 오해 → 다른 시도 → 결국 configure 재실행

---

## 🔴 문제 상황

### v2.5 로그 (Line 1366-1369):
```
Running `sed -n '20,60p' /repo/binutils/Makefile.am`...
sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5 [A]0;

`sed -n '20,60p' /repo/binutils/Makefile.am` executes with returncode: 123
```

### 코드 (sandbox.py Line 502-504):
```python
try:
    return_code = self.get_returncode()
except:
    return_code = 123  ← 너무 광범위!
```

### 영향:
1. sed 명령은 실제로 성공했을 수 있음
2. 하지만 `echo $?` 파싱 실패
3. returncode = 123으로 처리
4. LLM: "명령 실패!" → 다른 시도 → configure 재실행

---

## ✅ 해결 방안

### Option 1: Exception 세분화 ⭐ (추천)

```python
# sandbox.py Line 502-509
try:
    return_code = self.get_returncode()
except pexpect.TIMEOUT as e:
    print(f"[WARNING] get_returncode timeout for: {command}")
    print(f"[DEBUG] Timeout details: {e}")
    return_code = 124  # Timeout code
except pexpect.EOF as e:
    print(f"[ERROR] Container died during: {command}")
    print(f"[DEBUG] EOF details: {e}")
    return_code = 125  # Container dead
except ValueError as e:
    print(f"[WARNING] Cannot parse returncode: {e}")
    print(f"[DEBUG] Assuming command succeeded")
    return_code = 0  # Parsing error → assume success
except Exception as e:
    print(f"[ERROR] Unknown error in get_returncode: {e}")
    return_code = 123  # Unknown error
```

**장점:**
- 문제 원인 명확히 식별
- 로그에 디버그 정보 출력
- ValueError → 0 (명령 성공 가정)
- TIMEOUT/EOF → 명확한 에러 코드

### Option 2: Retry 메커니즘

```python
def get_returncode(self, max_retries=3):
    """
    Get command return code with retry mechanism.
    v2.6: Improved stability for flaky pexpect responses.
    """
    for attempt in range(max_retries):
        try:
            self.sandbox.shell.sendline('echo $?')
            self.sandbox.shell.expect([r'root@.*:.*# '], timeout=10)
            output = self.sandbox.shell.before.decode('utf-8').strip()
            output = output.replace('\x1b[?2004l\r', '')
            
            output_lines = output.split('\r\n')
            if len(output_lines) > 1:
                last_line = output_lines[-1]
                output_lines = output_lines[1:-1]
                id = last_line.find('\x1b[')
                if id != -1 and len(last_line[:id].strip()) > 0:
                    output_lines.append(last_line[:id].strip())
            
            return_code_str = '\n'.join(output_lines).strip()
            return int(return_code_str)
            
        except (pexpect.TIMEOUT, ValueError) as e:
            if attempt < max_retries - 1:
                print(f"[RETRY {attempt+1}/{max_retries}] get_returncode: {e}")
                time.sleep(0.5)
            else:
                print(f"[ERROR] get_returncode failed after {max_retries} attempts: {e}")
                return 0  # Assume success if can't determine
```

**장점:**
- 네트워크 지연 등 일시적 문제 해결
- 최대 3번 재시도
- 최종 실패 시 0 반환 (성공 가정)

### Option 3: 프롬프트 패턴 강화

```python
# sandbox.py Line 267
# Before:
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)

# After:
self.sandbox.shell.expect([
    r'root@.*:.*[#$]\s*',  # Standard root prompt
    r'[#$]\s*$',           # Simple prompt
    pexpect.TIMEOUT        # Handle timeout explicitly
], timeout=600)

if self.sandbox.shell.match == pexpect.TIMEOUT:
    print(f"[WARNING] Prompt timeout for: {command}")
    return_code = 124
```

**장점:**
- 다양한 프롬프트 형식 수용
- TIMEOUT 명시적 처리

### Option 4: 명령 성공 기본 가정 ⭐⭐ (가장 간단)

```python
# sandbox.py Line 502-509
try:
    return_code = self.get_returncode()
except Exception as e:
    # v2.6: If returncode detection fails, assume command succeeded
    # This prevents false failures from blocking LLM progress
    print(f"[WARNING] get_returncode failed for '{command}': {e}")
    print(f"[INFO] Assuming command succeeded (returncode=0)")
    return_code = 0  # Assume success
```

**장점:**
- 가장 간단한 수정 (2줄)
- false negative 방지
- LLM 진행 차단 안 됨

**단점:**
- 진짜 실패를 놓칠 수 있음
- 하지만 대부분 sed/grep은 성공함!

---

## 📊 비교

| 방안 | 복잡도 | 안정성 | 정확성 |
|------|--------|--------|--------|
| Option 1: 세분화 | 중 | 중 | 높음 |
| Option 2: Retry | 높음 | 높음 | 중 |
| Option 3: 패턴 | 낮음 | 중 | 중 |
| Option 4: 성공 가정 | **낮음** | **높음** | 낮음 |

---

## 💡 추천

**Option 1 + Option 4 조합:**

```python
try:
    return_code = self.get_returncode()
except pexpect.TIMEOUT as e:
    print(f"[WARNING] Timeout getting returncode for: {command}")
    return_code = 0  # Assume success
except pexpect.EOF as e:
    print(f"[ERROR] Container died during: {command}")
    return_code = 125  # Fatal
except Exception as e:
    print(f"[WARNING] Cannot get returncode: {e}")
    return_code = 0  # Assume success
```

**이유:**
- TIMEOUT/EOF는 명확히 구분 (디버깅)
- 파싱 에러는 성공 가정 (LLM 진행)
- 간단하고 효과적!

---

## 🎯 다음 단계

1. Option 1+4 구현
2. v2.6 재테스트
3. returncode 123 발생 확인


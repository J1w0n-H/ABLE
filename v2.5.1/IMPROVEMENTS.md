# ARVO v2.5.1 개선사항

## 문제 분석 결과

### 답지 빌드 (수동 테스트)
```bash
1. apt-get update -qq
2. apt-get install -y libgmp-dev libmpfr-dev
3. ./configure
4. make -j4 → Error 127: makeinfo not found
5. apt-get install -y texinfo && make -j4 → Error 127: flex/bison
6. apt-get install -y flex bison && make -j4 → 성공!
```

### v2.5 실패 원인
1. **타임아웃**: `apt-get install texinfo` 600초 초과 (41개 의존성)
2. **명령 분리**: 타임아웃으로 `make -j4`가 실행 안됨
3. **디렉토리 변경**: 타임아웃 후 쉘 재시작으로 `/src`로 이동

---

## v2.5.1 개선사항

### 1. 동적 타임아웃 (sandbox.py)
```python
# v2.5: Dynamic timeout for apt-get commands
command_timeout = 600 * 2  # Default 20 minutes
if 'apt-get install' in command:
    command_timeout = 1800  # 30 minutes for package installation

self.sandbox.shell.expect([r'root@.*:.*# '], timeout=command_timeout)
```

**효과**:
- apt-get 명령: 1800초 (30분)
- 기타 명령: 1200초 (20분)
- texinfo 설치 완료 가능

### 2. `-y` 플래그 자동 추가 (error_parser.py)
```python
# Before
suggestions.add(f"apt-get install {pkg}")

# After
suggestions.add(f"apt-get install -y {pkg}")
```

**효과**:
- 무인 설치 보장
- 사용자 입력 대기 방지

### 3. `: not found` 패턴 추가 (error_parser.py)
```python
error_patterns = [
    r'\*\*\* \[.+?\] Error \d+',
    r'error:',
    r'fatal error:',
    r'undefined reference to',
    r'No such file or directory',
    r'command not found',
    r': not found',  # ← 추가!
    r'configure: error:',
    r'Error \d+',
]
```

**효과**:
- `makeinfo: not found` 감지
- `flex: not found` 감지
- `bison: not found` 감지

---

## 수정된 파일

1. **build_agent/utils/sandbox.py**
   - Line 461-464: 동적 타임아웃 추가
   - Line 483: `command_timeout` 적용

2. **build_agent/utils/error_parser.py**
   - Line 54: `: not found` 패턴 추가
   - Line 234: `-y` 플래그 추가 (Error 127)
   - Line 258: `-y` 플래그 추가 (Missing headers)

---

## 예상 효과

### Before (v2.5)
```
make -j4 → Error 127: makeinfo
⛔ apt-get install texinfo && make -j4
→ apt-get 600초 타임아웃
→ make -j4 실행 안됨
→ 실패!
```

### After (v2.5.1)
```
make -j4 → Error 127: makeinfo
⛔ apt-get install -y texinfo && make -j4
→ apt-get 1800초 타임아웃 (성공!)
→ make -j4 실행 (Error 127: flex/bison)
→ apt-get install -y flex bison && make -j4
→ 성공!
```

---

## 검증 계획

1. binutils-gdb 재테스트
2. OpenSC 재테스트 (bootstrap 반복 문제)
3. 성공률 비교: v2.5 vs v2.5.1


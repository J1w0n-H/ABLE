# sandbox.py Command Pattern 리팩토링 (v2.2)

## 📋 작업 완료

### 1. ✅ helpers.py 생성
**목적**: 순환 import 해결

**내용**:
```python
# build_agent/utils/helpers.py
- SAFE_COMMANDS 상수
- truncate_msg() 함수
- get_waitinglist_error_msg() 함수
- get_conflict_error_msg() 함수
```

**효과**: sandbox.py ↔ command_handlers.py 순환 import 해결

---

### 2. ✅ command_handlers.py 수정
**변경**:
```python
# Before:
from sandbox import truncate_msg

# After:
from helpers import truncate_msg, SAFE_COMMANDS, get_waitinglist_error_msg, get_conflict_error_msg
```

**효과**: 독립적인 모듈 (순환 의존성 제거)

---

### 3. ✅ sandbox.py Feature Flag 통합

#### Import 변경:
```python
# Before:
safe_cmd = [...]  # 30줄
def truncate_msg(...):  # 20줄

# After:
from helpers import truncate_msg, SAFE_COMMANDS

# Feature flag
USE_COMMAND_PATTERN = os.getenv('ARVO_USE_COMMAND_PATTERN', 'false').lower() == 'true'
safe_cmd = SAFE_COMMANDS  # 하위 호환성
```

#### Session.__init__ 수정:
```python
def __init__(self, sandbox):
    self.sandbox = sandbox
    
    # CommandExecutor 초기화 (feature flag)
    self.command_executor = None
    if USE_COMMAND_PATTERN:
        try:
            from command_handlers import CommandExecutor
            self.command_executor = CommandExecutor()
            print('[INFO] Command Pattern enabled')
        except ImportError as e:
            print(f'[WARNING] Command Pattern not available: {e}')
```

#### execute() 메서드 수정:
```python
def execute(self, command, waiting_list, conflict_list, timeout=600):
    """Execute command with optional Command Pattern routing"""
    try:
        # NEW: Try Command Pattern first (if enabled)
        if USE_COMMAND_PATTERN and self.command_executor:
            return self.command_executor.execute(
                command, self, waiting_list, conflict_list, timeout
            )
        
        # ORIGINAL: Legacy logic (stable)
        if 'hatch shell' == command.lower().strip():
            # ... 기존 200줄 로직
```

---

## 🧪 사용 방법

### 기본 (Original Logic - 안정적):
```bash
cd /root/Git/ARVO2.0
python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0
```

### Command Pattern (새로운 방식 - 테스트):
```bash
cd /root/Git/ARVO2.0
export ARVO_USE_COMMAND_PATTERN=true
python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0
```

### 자동 테스트:
```bash
cd /root/Git/ARVO2.0
./test_command_pattern.sh
```

---

## 📊 Feature Flag 방식의 장점

### 1. ✅ 안전성
```
Flag OFF (기본값): 기존 로직 사용 → 안정적
Flag ON: Command Pattern 사용 → 테스트
```

### 2. ✅ 점진적 마이그레이션
```
Phase 1: Flag OFF로 운영 (현재)
Phase 2: Flag ON으로 테스트
Phase 3: 문제 없으면 기본값을 ON으로
Phase 4: 기존 로직 제거
```

### 3. ✅ 롤백 용이
```
문제 발생 시: export ARVO_USE_COMMAND_PATTERN=false
즉시 기존 로직으로 복귀
```

### 4. ✅ A/B 테스트
```
같은 프로젝트를 두 방식으로 실행하여 비교 가능
```

---

## 🎯 테스트 계획

### Phase 1: Hello World (현재)
```bash
# Original
ARVO_USE_COMMAND_PATTERN=false python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0

# Command Pattern
ARVO_USE_COMMAND_PATTERN=true python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0

# 비교:
# - 턴 수 동일한가?
# - 성공 여부 동일한가?
# - 출력 형식 동일한가?
```

### Phase 2: ImageMagick
```bash
# Original vs Pattern 비교
```

### Phase 3: 다양한 프로젝트
```bash
# cJSON, libpng, curl, zlib 등
```

---

## 🔍 예상 결과

### 성공 시 (동일한 결과):
```
Original:  4턴, ✅ Success
Pattern:   4턴, ✅ Success
→ Command Pattern 검증 완료!
→ Phase 4로 진행 (기본값 변경)
```

### 문제 발생 시:
```
Original:  4턴, ✅ Success
Pattern:   Error 또는 다른 결과
→ Command Pattern 디버깅
→ 또는 보류 (기존 로직 유지)
```

---

## 📁 변경된 파일 (3개)

| # | 파일 | 변경 내용 |
|---|-----|---------|
| 1 | helpers.py (NEW!) | SAFE_COMMANDS, truncate_msg, 에러 메시지 |
| 2 | command_handlers.py | helpers import로 변경 |
| 3 | sandbox.py | Feature flag + CommandExecutor 통합 |

---

## 🎯 현재 상태

### ✅ 완료:
- helpers.py 생성 (순환 import 해결)
- command_handlers.py 수정
- sandbox.py Feature flag 통합
- test_command_pattern.sh 생성

### ⏸️ 대기:
- 테스트 실행 및 검증
- 문제 발견 시 디버깅
- 문제 없으면 기본값 활성화

### 📋 다음 스텝:
```bash
# 테스트 실행
./test_command_pattern.sh

# 또는 수동으로:
export ARVO_USE_COMMAND_PATTERN=true
python build_agent/main.py dvyshnavi15/helloworld 2449df7 /root/Git/ARVO2.0
```

---

## 💡 설계 철학

### Backward Compatibility (하위 호환성)
```python
# 기본값: false (기존 로직)
USE_COMMAND_PATTERN = os.getenv('ARVO_USE_COMMAND_PATTERN', 'false').lower() == 'true'

# 기존 사용자: 영향 없음
# 새로운 기능 테스트: 환경 변수만 설정
```

### Fail-Safe (안전 장치)
```python
if USE_COMMAND_PATTERN:
    try:
        from command_handlers import CommandExecutor
        self.command_executor = CommandExecutor()
    except ImportError:
        # Import 실패 시 자동으로 기존 로직 사용
        self.command_executor = None
```

### Clean Code (깔끔한 코드)
```python
# Command Pattern 사용 시:
# - 200줄 execute() → 20줄
# - 각 Handler 독립적으로 테스트 가능
# - 새 명령 추가 쉬움
```

---

## 🚀 코드 복잡도 비교

### Before (Original Logic):
```
sandbox.py execute()
└── 200줄 (if-elif 체인)
    ├── Special commands (40줄)
    ├── Tool commands (80줄)
    ├── Validation (20줄)
    └── Bash execution (60줄)
```

### After (Command Pattern):
```
sandbox.py execute()
└── 20줄 (위임만)
    └─> command_handlers.py
        ├── PwdCommandHandler (15줄)
        ├── DownloadCommandHandler (10줄)
        ├── WaitingListAddHandler (15줄)
        ├── ... (15+ handlers)
        └── CommandExecutor (50줄)
```

**복잡도**: 200줄 → 20줄 (**90% 감소**)

---

**작성일**: 2025-10-19  
**상태**: ✅ 구현 완료, 테스트 대기  
**리스크**: Medium (Feature flag로 안전하게 관리)  
**다음**: 테스트 실행 및 검증


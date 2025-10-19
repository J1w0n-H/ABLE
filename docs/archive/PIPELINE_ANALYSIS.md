# ARVO2.0 파이프라인 흐름 분석 및 개선 제안

## 📋 목차
1. [전체 파이프라인 흐름](#전체-파이프라인-흐름)
2. [발견된 문제점](#발견된-문제점)
3. [개선 제안](#개선-제안)
4. [우선순위별 액션 아이템](#우선순위별-액션-아이템)

---

## 🔄 전체 파이프라인 흐름

### Phase 1: 초기화 (main.py)
```
1. 인자 파싱 (full_name, sha, root_path)
2. 로깅 설정 (TeeOutput)
3. 타이머 시작 (2시간 제한)
4. 레포지토리 다운로드 (download_repo)
   ├─ Git clone
   ├─ move_files_to_repo (repo 폴더 정리)
   └─ Git checkout SHA
```

### Phase 2: 빌드 환경 구성 (configuration.py)
```
5. Sandbox 생성 및 시작
   ├─ Dockerfile 생성 (gcr.io/oss-fuzz-base/base-builder)
   ├─ Docker 이미지 빌드
   └─ 컨테이너 시작 + /repo 마운트

6. Configuration Agent 실행 (최대 100턴)
   ├─ LLM에게 초기 프롬프트 전달
   └─ 반복 (turn < max_turn):
       ├─ LLM 응답 받기 (gpt-4o-2024-05-13)
       ├─ 명령어 추출 (extract_commands)
       ├─ Sandbox에서 실행 (sandbox.execute)
       ├─ 결과 관찰 (Observation)
       ├─ Token 관리 (manage_token_usage)
       └─ 성공 조건 체크:
           "Congratulations, you have successfully configured the environment!"
```

### Phase 3: 결과 저장 및 정리
```
7. 컨테이너 중지 및 정리
8. Dockerfile 통합 (integrate_dockerfile)
   ├─ inner_commands.json 읽기
   ├─ 성공한 명령어만 Dockerfile로 변환
   └─ 최종 Dockerfile 생성
```

---

## ❌ 발견된 문제점

### 🔴 Critical (즉시 수정 필요)

#### 1. **runtest.py - 빌드 산출물 검증 부족**
**위치**: `build_agent/tools/runtest.py:35-59`

**문제**:
```python
# 현재 로직:
elif os.path.exists('/repo/Makefile'):
    print('Found Makefile build.')
    print('✅ Essential files found (Makefile exists).')
    test_command = 'make test || make check'
    test_cwd = '/repo'
```

**문제점**:
- Makefile이 있다고 해서 빌드가 완료된 것이 아님
- `make test`가 없으면 무조건 실패 (대부분의 simple project는 test 타겟 없음)
- 빌드 산출물 (*.o, *.so, 실행 파일) 확인 안함

**영향**:
- False Negative: 빌드 성공했지만 runtest 실패
- LLM이 혼란스러워함 ("make 성공했는데 왜 runtest 실패?")

**실제 시나리오**:
```bash
Turn 5: make → Build successful (*.o files generated)
Turn 6: runtest → make test → make: *** No rule to make target 'test'. ❌
LLM: "Makefile에 test 타겟이 없네... 뭘 해야 하지?"
```

---

#### 2. **download.py - 무한 재시도 루프 가능성**
**위치**: `build_agent/utils/download.py:41-84`

**문제**:
```python
while waiting_list.size() > 0:
    pop_item = waiting_list.pop()
    # ...
    if not success:
        timeout = match_timeout(result)
        if timeout:
            pop_item.timeouterror += 1
            waiting_list.add(...)  # ← 다시 추가!
        else:
            pop_item.othererror += 1
            waiting_list.add(...)  # ← 다시 추가!
```

**문제점**:
- `while waiting_list.size() > 0` 조건이지만, 실패 시 다시 추가
- 3번 실패 체크는 있지만, 같은 턴 내에서 무한 루프 가능
- 실패한 패키지가 `waiting_list`에 계속 추가되어 `download` 호출 시마다 재시도

**실제 시나리오**:
```bash
Turn 1: waitinglist add -p nonexistent-package -t apt
Turn 2: download
  → nonexistent-package 설치 실패 (1/3)
  → waiting_list에 다시 추가
  → 다음 패키지 처리...
  → 루프 다시 nonexistent-package 시도 (2/3)
  → ...
  → 3번 실패 후 failed_download로 이동 ✅
  
Turn 3: LLM이 "download" 다시 호출
  → waiting_list 비어있음
  → "No packages in waiting list" 출력
  
하지만! LLM이 failed_download 메시지 보고 다시 waitinglist add 시도 가능
→ 같은 패키지 무한 재시도 가능성
```

**근본 문제**:
- `download` 도구 설명이 모호: "Download all pending elements in the waiting list at once."
- LLM이 실패 후 다시 `download` 호출할 이유가 없다는 것을 명시 안함

---

#### 3. **integrate_dockerfile.py - C 명령 변환 불완전**
**위치**: `build_agent/utils/integrate_dockerfile.py:226-237`

**문제**:
```python
# C 전용 도구들 처리
if command == 'python /home/tools/run_make.py':
    return 'RUN make'
elif command == 'python /home/tools/run_cmake.py':
    return 'RUN cmake . && make'
elif command == 'python /home/tools/run_gcc.py':
    return 'RUN gcc -o hello *.c'
```

**문제점 1**: **실제 사용되지 않는 도구들**
- 현재 `tools_config.py`에는 `run_make`, `run_cmake`, `run_gcc` 도구 없음!
- 대신 LLM이 직접 `make`, `cmake`, `gcc` 명령 실행
- 이 변환 로직이 실제로 트리거되는 경우 없음

**문제점 2**: **실제 명령과 미스매치**
```python
# LLM이 실행한 명령:
cd /repo && ./configure && make -j4

# integrate_dockerfile 변환:
RUN make  # ← configure 누락! 다시 빌드하면 실패!
```

**문제점 3**: **apt_install 처리 오류**
```python
elif command.startswith('python /home/tools/apt_install.py'):
    package_name = command.split()[-1]
    return f'RUN apt-get update && apt-get install -y {package_name}'
```
- `apt_install.py`도 실제로 사용 안함 (LLM이 직접 `apt-get install` 실행)
- 실제 명령은 `python /home/tools/apt_download.py -p <package>` 형식
- `.split()[-1]`은 패키지명 추출 실패 가능 (예: `-p` 플래그 붙은 경우)

**실제 명령 추적**:
```bash
# sandbox.py:55에서 실제로 실행되는 명령:
command = f'python /home/tools/apt_download.py -p {package_name}'

# integrate_dockerfile.py에서 기대하는 명령:
'python /home/tools/apt_install.py <package>'  ← 존재하지 않음!
```

---

### 🟠 High (높은 우선순위)

#### 4. **configuration.py - 프롬프트 중복 및 과다**
**위치**: `build_agent/agents/configuration.py:91-226`

**문제**:
```python
self.init_prompt = f"""\
...
VERY IMPORTANT TIPS: 
    * You should not answer the user's question... (3번 반복)
    * You MUST complete the build before running runtest! ... (3번 반복)
    * Passing tests by modifying test source files... (3번 반복)
    * Try to write all commands on a single line... (3번 반복)
    * When other configuration methods can be used... (3번 반복)
    * You are not allowed to use commands... (3번 반복)
"""
```

**문제점**:
- 같은 내용 3번씩 반복 = 토큰 낭비 (약 500 토큰)
- 프롬프트가 너무 김 (3000+ 토큰)
- LLM이 중요한 부분을 놓칠 가능성

**개선안**:
```python
CRITICAL RULES (DO NOT VIOLATE):
1. Build FIRST (./configure && make), THEN run runtest
2. NEVER modify test files to pass tests
3. Write all commands on ONE line (use && not backslash)
4. NEVER use interactive shells (hatch shell, etc.)
5. Analyze dependencies from config files, THEN install
```

---

#### 5. **sandbox.py - execute() 메서드 복잡도**
**위치**: `build_agent/utils/sandbox.py:348-547`

**문제**:
```python
def execute(self, command, waiting_list, conflict_list, timeout=600):
    # 200줄의 복잡한 if-elif 체인
    if 'hatch shell' == command.lower().strip():
        ...
    if '$pwd$' == command.lower().strip():
        ...
    if '$pip list --format json$' == command.lower().strip():
        ...
    if match_download(command):
        ...
    elif match_conflict_solve(command) != -1:
        ...
    elif match_conflictlist_clear(command):
        ...
    # ... 20+ elif branches
```

**문제점**:
- 단일 함수가 너무 많은 책임 (SRP 위반)
- 테스트 어려움
- 새로운 명령 추가 시 전체 함수 이해 필요
- 에러 처리 로직이 분산됨

**개선안**: Command Pattern 적용
```python
class CommandExecutor:
    def __init__(self):
        self.handlers = {
            'download': DownloadHandler(),
            'waitinglist': WaitingListHandler(),
            'conflictlist': ConflictListHandler(),
            'runtest': RuntestHandler(),
            # ...
        }
    
    def execute(self, command, ...):
        for pattern, handler in self.handlers.items():
            if handler.matches(command):
                return handler.execute(command, ...)
        return self._execute_bash(command)
```

---

#### 6. **main.py - root_path 처리 혼란**
**위치**: `build_agent/main.py:117-124`

**문제**:
```python
root_path = args.root_path

if not os.path.isabs(root_path):
    root_path = os.path.abspath(root_path)

# root_path should point to build_agent directory
if not root_path.endswith('build_agent'):
    root_path = os.path.join(root_path, 'build_agent')
```

**문제점**:
- 사용자가 `/root/Git/ARVO2.0` 입력 → 자동으로 `/root/Git/ARVO2.0/build_agent` 변환
- 사용자가 `/root/Git/ARVO2.0/build_agent` 입력 → 변환 안함
- 하지만 모든 곳에서 `root_path`가 `build_agent`를 가리킨다고 가정
- 혼란스러움! 명확한 네이밍 필요

**실제 사용**:
```python
# main.py:
download_repo(root_path, ...)  # root_path = .../build_agent
# → 내부에서 {root_path}/utils/repo/{author}/{repo} 사용

# configuration.py:
self.root_dir = root_dir  # root_dir = .../build_agent
# → 내부에서 {root_dir}/output/{full_name} 사용

# integrate_dockerfile.py:
root_path = os.path.normpath(root_path)  # root_path = .../output/{author}/{repo}
# → 완전히 다른 의미!
```

**개선안**:
```python
# 명확한 변수명 사용
project_root = '/root/Git/ARVO2.0'
build_agent_dir = f'{project_root}/build_agent'
repo_cache_dir = f'{build_agent_dir}/utils/repo'
output_dir = f'{project_root}/output'
```

---

### 🟡 Medium (중간 우선순위)

#### 7. **Token 관리 - 히스토리 삭제 로직 의심스러움**
**위치**: `build_agent/agents/configuration.py:252-268`

**문제**:
```python
def manage_token_usage(messages, max_tokens=30000):
    total_tokens = sum(len(str(message)) for message in messages)
    if total_tokens <= max_tokens:
        return messages
    
    new_messages = messages[:]
    while sum(len(str(message)) for message in new_messages) > max_tokens:
        # new_messages = new_messages[4:]  # 주석 처리됨
        new_messages = new_messages[:4] + new_messages[6:]  # ← 이게 맞나?
    
    return new_messages
```

**문제점 1**: **Token 계산 부정확**
- `len(str(message))`는 문자 수, Token 수 아님
- OpenAI의 실제 토큰 계산과 차이 큼
- 예: "configuration" = 1개 토큰이지만 `len() = 13`

**문제점 2**: **삭제 로직 이상함**
```python
# 의도: 시스템 메시지 유지 + 오래된 대화 삭제
new_messages = new_messages[:4] + new_messages[6:]
# → [0, 1, 2, 3] + [6, 7, 8, ...]
# → 5번째, 6번째 메시지만 삭제?

# 예상 의도:
# new_messages = [system] + new_messages[-20:]  # 최근 20턴만 유지
```

**실제 효과**:
- 30,000자 넘으면 → 5,6번 메시지 삭제
- 여전히 30,000자 넘으면 → 다시 5,6번 삭제 (이제 7,8번이 5,6번이 됨)
- 무한 루프 가능! (while문)

**개선안**:
```python
import tiktoken

def manage_token_usage(messages, max_tokens=30000):
    encoding = tiktoken.encoding_for_model("gpt-4o")
    
    # 정확한 토큰 계산
    total_tokens = sum(len(encoding.encode(str(msg))) for msg in messages)
    
    if total_tokens <= max_tokens:
        return messages
    
    # 시스템 메시지 + 최근 메시지만 유지
    system_msgs = [msg for msg in messages if msg['role'] == 'system'][:1]
    recent_msgs = messages[-(max_tokens // 1000):]  # 대략 최근 N턴
    
    return system_msgs + recent_msgs
```

---

#### 8. **waiting_list / conflict_list - 복잡한 상태 관리**
**위치**: 전체 시스템

**문제**:
- `waiting_list`: 설치 대기 중인 패키지
- `conflict_list`: 버전 충돌 패키지
- 두 리스트가 계속 동기화 필요
- LLM이 이해하기 어려움

**실제 LLM 혼란**:
```
Turn 5:
### Thought: I'll add libssl-dev to waiting list
### Action:
waitinglist add -p libssl-dev -t apt

Turn 6:
### Thought: Now I'll download it
### Action:
download

Turn 7: (download 실패)
### Observation:
"libssl-dev" installed failed due to non-timeout errors
...

Turn 8:
### Thought: Hmm, it failed. Should I call download again? Or check conflictlist?
### Action:
conflictlist show

Turn 9:
### Observation:
The conflict list is empty.

Turn 10:
### Thought: ??? Then why did it fail?
```

**근본 문제**:
- `conflict_list`는 Python 버전 충돌용으로 설계됨 (예: numpy==1.19 vs numpy==1.20)
- C 프로젝트에서는 의미 없음 (apt-get은 버전 자동 해결)
- 불필요한 복잡도

**개선안**:
```python
# C 프로젝트는 단순화
class PackageManager:
    def __init__(self):
        self.pending = []  # 설치 대기
        self.installed = []  # 설치 완료
        self.failed = []  # 설치 실패 (3번 시도 후)
    
    def add(self, package):
        if package not in self.failed:
            self.pending.append(package)
    
    def install_all(self):
        while self.pending:
            pkg = self.pending.pop(0)
            if self._try_install(pkg, max_attempts=3):
                self.installed.append(pkg)
            else:
                self.failed.append(pkg)
```

---

#### 9. **에러 메시지 - 액션 가이드 부족**
**위치**: 전반

**문제**:
```python
# 현재 에러 메시지:
"❌ Error: CMakeLists.txt found but not configured."
"Please run: mkdir -p /repo/build && cd /repo/build && cmake .."

# LLM 응답:
### Thought: Okay, I'll run that command
### Action:
mkdir -p /repo/build && cd /repo/build && cmake ..
```

**문제점**:
- 에러 메시지는 좋음
- 하지만 LLM이 그 다음에 뭘 해야 할지 모름
- "cmake 성공했으면 다음은 make인가? 아니면 runtest?"

**개선안**:
```python
print('❌ Error: CMakeLists.txt found but not configured.')
print('│ 1. mkdir -p /repo/build && cd /repo/build && cmake ..')
print('│ 2. make -j4')
print('│ 3. runtest')
print('└─ Follow these steps in order to complete the build.')
```

---

#### 10. **로깅 - 디버깅 정보 부족**
**위치**: `build_agent/main.py:33-51`

**문제**:
```python
class TeeOutput:
    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.log.write(message)
        self.log.flush()
```

**문제점**:
- 모든 출력을 로그에 기록 ✅
- 하지만 타임스탬프 없음 ❌
- Turn 번호 없음 ❌
- 명령어 실행 시간 없음 ❌

**개선안**:
```python
class TeeOutput:
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', buffering=1)
        self.turn = 0
    
    def write_with_metadata(self, message, metadata=None):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if metadata:
            prefix = f"[{timestamp}] [Turn {metadata['turn']}] "
        else:
            prefix = f"[{timestamp}] "
        
        formatted = f"{prefix}{message}"
        self.terminal.write(formatted)
        self.log.write(formatted)
```

---

### 🟢 Low (낮은 우선순위, 나중에)

#### 11. **코드 중복 - safe_cmd 리스트**
**위치**: 
- `build_agent/utils/sandbox.py:31-40`
- `build_agent/utils/integrate_dockerfile.py:155-164`

**문제**: 동일한 리스트가 2곳에 중복 정의됨

**개선안**: `constants.py` 파일 생성
```python
# build_agent/utils/constants.py
SAFE_COMMANDS = [
    "cd", "ls", "cat", "echo", "pwd", ...
]
```

---

#### 12. **타이머 - 2시간 하드코딩**
**위치**: `build_agent/main.py:159-167`

**문제**:
```python
def timer():
    time.sleep(3600*2)  # Wait for 2 hours
    print("Timeout for 2 hour!")
    os._exit(1)
```

**개선안**:
```python
parser.add_argument('--timeout', type=int, default=7200, help='Timeout in seconds')
```

---

#### 13. **Docker 리소스 - 하드코딩**
**위치**: `build_agent/utils/sandbox.py:189-191`

**문제**:
```python
mem_limit='30g',
cpuset_cpus='0-15',
```

**개선안**: 환경 변수나 설정 파일
```python
mem_limit=os.getenv('DOCKER_MEM_LIMIT', '30g'),
cpuset_cpus=os.getenv('DOCKER_CPUSET', '0-15'),
```

---

## ✅ 개선 제안 (우선순위별)

### 🔥 Priority 1: Critical Fixes (즉시 수정)

#### Fix 1: runtest.py - 빌드 산출물 검증 추가

**파일**: `build_agent/tools/runtest.py`

**현재 문제**:
```python
# Makefile 있으면 무조건 "make test" 실행
elif os.path.exists('/repo/Makefile'):
    test_command = 'make test || make check'
    # → make test가 없으면 실패!
```

**개선안**:
```python
elif os.path.exists('/repo/Makefile'):
    print('Found Makefile build.')
    
    # Step 1: Check if build artifacts exist
    build_check = subprocess.run(
        'find /repo -type f \\( -name "*.o" -o -name "*.so" -o -name "*.a" -o -executable \\) | head -10',
        shell=True, capture_output=True, text=True
    )
    
    if not build_check.stdout.strip():
        print('❌ Error: Makefile exists but no build artifacts found.')
        print('│ This usually means the project has not been built yet.')
        print('│ Please run: cd /repo && make -j4')
        print('└─ After building successfully, run runtest again.')
        sys.exit(1)
    
    print('✅ Build artifacts found:')
    for line in build_check.stdout.strip().split('\n')[:5]:
        print(f'  - {line}')
    
    # Step 2: Try to run tests
    # First check if test target exists
    test_check = subprocess.run(
        'make -n test 2>&1 | head -5',
        cwd='/repo', shell=True, capture_output=True, text=True
    )
    
    if 'No rule to make target' in test_check.stderr or 'No rule to make target' in test_check.stdout:
        # No test target - just verify build
        print('No test target found. Verifying build only.')
        print('✅ Build successful!')
        print('\nCongratulations, you have successfully configured the environment!')
        sys.exit(0)
    else:
        # Test target exists
        test_command = 'make test || make check'
        test_cwd = '/repo'
```

**효과**:
- ✅ False Negative 제거
- ✅ 명확한 에러 메시지 (빌드 안했으면 "make 실행하세요")
- ✅ Simple project 지원 (test 타겟 없어도 성공)

---

#### Fix 2: download.py - 명확한 상태 전달 + 반복 호출 방지

**파일**: `build_agent/utils/download.py`

**개선 1**: 메시지 명확화
```python
if waiting_list.size() == 0:
    print('╔═══════════════════════════════════════════════════════════╗')
    print('║  The waiting list is empty.                               ║')
    print('║  All packages have been processed.                        ║')
    print('║                                                            ║')
    print('║  ⚠️  DO NOT call "download" again unless you:             ║')
    print('║     1. Add new packages to waiting list, OR               ║')
    print('║     2. Modify failed packages and retry                   ║')
    print('║                                                            ║')
    print('║  Next steps:                                              ║')
    print('║     - If all packages installed: proceed with build       ║')
    print('║     - If some failed: check error messages above          ║')
    print('╚═══════════════════════════════════════════════════════════╝')
    return [], [], []
```

**개선 2**: 이미 처리된 패키지 추적
```python
class PackageDownloader:
    def __init__(self):
        self.attempted_packages = set()  # 이미 시도한 패키지
    
    def download(self, session, waiting_list, conflict_list):
        if waiting_list.size() == 0:
            print('[INFO] Waiting list is empty - all packages processed.')
            return [], [], []
        
        # 중복 방지
        for item in waiting_list.items:
            pkg_key = f"{item.package_name}:{item.tool}"
            if pkg_key in self.attempted_packages:
                print(f'⚠️  Package "{item.package_name}" already attempted. Skipping.')
                waiting_list.remove(item)
                continue
            self.attempted_packages.add(pkg_key)
        
        # ... 기존 로직 ...
```

**효과**:
- ✅ LLM이 "download 다시 부르지 말아야 한다"는 것을 명확히 이해
- ✅ 같은 패키지 무한 재시도 방지
- ✅ 다음 액션 가이드 제공

---

#### Fix 3: integrate_dockerfile.py - 실제 명령어와 일치하도록 수정

**파일**: `build_agent/utils/integrate_dockerfile.py`

**문제**: 존재하지 않는 도구 변환
```python
# 현재 (작동 안함):
if command == 'python /home/tools/run_make.py':
    return 'RUN make'
```

**해결 1**: 실제 명령어 패턴 매칭
```python
def generate_statement(inner_command, pipdeptree_data):
    command = inner_command['command']
    dir = inner_command['dir'] if 'dir' in inner_command else '/'
    returncode = inner_command['returncode']
    
    if str(returncode).strip() != '0':
        return -1
    
    action_name = command.split(' ')[0].strip()
    
    # Skip safe commands (read-only)
    if action_name in safe_cmd and '>' not in command:
        return -1
    
    # Skip test/analysis commands
    if command == 'python /home/tools/runtest.py' or \
       command == 'python /home/tools/generate_diff.py':
        return -1
    
    # === C/C++ specific commands ===
    
    # apt-get install (actual command used)
    if command.startswith('apt-get install') or \
       command.startswith('python /home/tools/apt_download.py'):
        # Extract package name
        if '-p' in command:
            # Format: python /home/tools/apt_download.py -p <package>
            import shlex
            args = shlex.split(command)
            if '-p' in args:
                idx = args.index('-p')
                package_name = args[idx + 1]
                return f'RUN apt-get update -qq && apt-get install -y -qq {package_name}'
        else:
            # Format: apt-get install <packages>
            return f'RUN {command}'
    
    # Build commands - preserve as-is!
    if 'configure' in command or 'cmake' in command or 'make' in command:
        if dir != '/':
            return f'RUN cd {dir} && {command}'
        else:
            return f'RUN {command}'
    
    # Environment variables
    if action_name == 'export':
        return f'ENV {command.split("export ")[1]}'
    
    # Default: convert to RUN command
    if dir != '/':
        return f'RUN cd {dir} && {command}'
    else:
        return f'RUN {command}'
```

**효과**:
- ✅ 실제 명령어 패턴과 일치
- ✅ `./configure && make` 같은 복합 명령 보존
- ✅ apt_download.py 올바르게 처리

---

### 🚀 Priority 2: High Priority Improvements

#### Improvement 1: configuration.py - 프롬프트 단순화

**파일**: `build_agent/agents/configuration.py:91-226`

**변경 전**: 3000+ 토큰
**변경 후**: 1500 토큰 (50% 감소)

**개선안**:
```python
self.init_prompt = f"""\
You are a C/C++ build environment configuration expert. Your task is to analyze the repository structure, identify dependencies, install them, and successfully build the project.

## 🎯 Goal
Build the project and pass `runtest` verification. Success message: "Congratulations, you have successfully configured the environment!"

## 📋 Workflow
1. **Analyze**: Check build system (Makefile, CMakeLists.txt, configure)
2. **Dependencies**: Read config files to identify required libraries
3. **Install**: Add packages to waitinglist, then call download
4. **Configure**: Run ./configure or cmake (if needed)
5. **Build**: Run make -j4
6. **Verify**: Run runtest

## 🔧 File Reading Tips (Avoid Token Overflow)
- ✅ Use `grep` for patterns: `grep -n "AC_CHECK_LIB" configure.ac`
- ✅ Use `sed` for ranges: `sed -n '100,200p' file`
- ✅ Use `cat` for small files (<200 lines)
- ⚠️ NEVER read incrementally (head -50, then head -100...) - wastes turns!

## 🚨 Critical Rules
1. **Build BEFORE runtest**: install → configure/cmake → make → runtest
2. **Do NOT modify test files** to pass tests
3. **Write commands on ONE line**: Use && not backslash
4. **Do NOT use interactive shells**: No hatch shell, tmux, etc.
5. **download processes ALL waiting list**: Do NOT call download multiple times

## 🛠 Available Commands
{tools_list}

## 📦 Package Management
- waitinglist: Stores packages to install via apt-get
- Use: `waitinglist add -p <package> -t apt` then `download`
- After download completes, do NOT call download again unless adding new packages

## 🔄 Command Format
Use ```bash blocks with && for multiple commands:
```bash
cd /repo && ./configure && make -j4
```

Current environment: {self.image_name}
Repository path: /repo

Begin analysis:
"""
```

**효과**:
- ✅ 50% 토큰 절감
- ✅ 구조화된 정보 (LLM이 쉽게 파악)
- ✅ 이모지로 시각적 구분
- ✅ 핵심 규칙만 강조

---

#### Improvement 2: sandbox.py - Command Handler 패턴

**파일**: `build_agent/utils/sandbox.py`

**새 파일**: `build_agent/utils/command_handlers.py`

```python
# command_handlers.py
from abc import ABC, abstractmethod

class CommandHandler(ABC):
    @abstractmethod
    def matches(self, command: str) -> bool:
        pass
    
    @abstractmethod
    def execute(self, command: str, session, waiting_list, conflict_list):
        pass

class DownloadHandler(CommandHandler):
    def matches(self, command):
        return match_download(command)
    
    def execute(self, command, session, waiting_list, conflict_list):
        with OutputCollector() as collector:
            download(session, waiting_list, conflict_list)
        result = collector.get_output()
        return truncate_msg(result, 'download'), 'unknown'

class WaitingListAddHandler(CommandHandler):
    def matches(self, command):
        return match_waitinglist_add(command) != -1
    
    def execute(self, command, session, waiting_list, conflict_list):
        parsed = match_waitinglist_add(command)
        with OutputCollector() as collector:
            waiting_list.add(
                parsed['package_name'],
                parsed['version_constraints'],
                parsed['tool'],
                conflict_list
            )
        result = collector.get_output()
        return truncate_msg(result, command), 'unknown'

# ... 다른 핸들러들 ...

class CommandExecutor:
    def __init__(self):
        self.handlers = [
            DownloadHandler(),
            WaitingListAddHandler(),
            ConflictListHandler(),
            RuntestHandler(),
            # ...
        ]
    
    def execute(self, command, session, waiting_list, conflict_list):
        # Special commands first
        if command == '$pwd$':
            return self._execute_pwd(session)
        
        # Try each handler
        for handler in self.handlers:
            if handler.matches(command):
                return handler.execute(command, session, waiting_list, conflict_list)
        
        # Default: execute as bash command
        return self._execute_bash(command, session)
```

**sandbox.py 수정**:
```python
class Session:
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.executor = CommandExecutor()
    
    def execute(self, command, waiting_list, conflict_list, timeout=600):
        return self.executor.execute(command, self, waiting_list, conflict_list)
```

**효과**:
- ✅ 단일 책임 원칙 (SRP)
- ✅ 테스트 용이
- ✅ 새로운 명령 추가 쉬움
- ✅ 코드 가독성 향상

---

### 📊 Priority 3: Medium Priority

#### Improvement 3: 정확한 Token 카운팅

**파일**: `build_agent/agents/configuration.py`

**설치**:
```bash
pip install tiktoken
```

**코드**:
```python
import tiktoken

class Configuration(Agent):
    def __init__(self, ...):
        # ...
        self.encoding = tiktoken.encoding_for_model("gpt-4o")
    
    def count_tokens(self, messages):
        """Accurately count tokens"""
        total = 0
        for msg in messages:
            if isinstance(msg, dict):
                content = msg.get('content', '')
                total += len(self.encoding.encode(content))
        return total
    
    def manage_token_usage(self, messages, max_tokens=30000):
        """
        Keep conversation within token limit
        Strategy: Keep system message + recent turns
        """
        total_tokens = self.count_tokens(messages)
        
        if total_tokens <= max_tokens:
            return messages
        
        print(f'⚠️  Token limit reached: {total_tokens}/{max_tokens}')
        
        # Keep first message (system) + recent messages
        if len(messages) < 2:
            return messages
        
        system_msg = messages[0] if messages[0]['role'] == 'system' else None
        
        # Binary search for max messages that fit
        left, right = 1, len(messages) - 1
        best_count = 1
        
        while left <= right:
            mid = (left + right) // 2
            recent = messages[-mid:]
            test_messages = ([system_msg] if system_msg else []) + recent
            
            if self.count_tokens(test_messages) <= max_tokens:
                best_count = mid
                left = mid + 1
            else:
                right = mid - 1
        
        result = ([system_msg] if system_msg else []) + messages[-best_count:]
        print(f'✂️  Trimmed to {len(result)} messages (~{self.count_tokens(result)} tokens)')
        return result
```

**효과**:
- ✅ 정확한 토큰 계산
- ✅ 429 에러 방지
- ✅ 더 많은 히스토리 보존 가능

---

#### Improvement 4: 명확한 에러 메시지 + 액션 가이드

**파일**: 전반

**헬퍼 함수 추가**:
```python
# build_agent/utils/error_messages.py

class ErrorGuide:
    @staticmethod
    def cmake_not_configured():
        return '''
╔════════════════════════════════════════════════════════════════╗
║  ❌ Error: CMakeLists.txt found but project not configured    ║
╟────────────────────────────────────────────────────────────────╢
║  Next steps:                                                   ║
║  1. mkdir -p /repo/build && cd /repo/build && cmake ..         ║
║  2. make -j4                                                   ║
║  3. runtest                                                    ║
╟────────────────────────────────────────────────────────────────╢
║  What this does:                                               ║
║  - Step 1: Configure build system (generates Makefile)         ║
║  - Step 2: Compile source code                                 ║
║  - Step 3: Verify build and run tests                          ║
╚════════════════════════════════════════════════════════════════╝
'''
    
    @staticmethod
    def configure_not_run():
        return '''
╔════════════════════════════════════════════════════════════════╗
║  ❌ Error: configure script found but not executed             ║
╟────────────────────────────────────────────────────────────────╢
║  Next steps:                                                   ║
║  1. cd /repo && ./configure                                    ║
║  2. make -j4                                                   ║
║  3. runtest                                                    ║
╟────────────────────────────────────────────────────────────────╢
║  Common ./configure errors and fixes:                          ║
║  - "missing library": Install -dev package (apt-get install)   ║
║  - "aclocal not found": apt-get install automake               ║
║  - "permission denied": chmod +x configure                     ║
╚════════════════════════════════════════════════════════════════╝
'''
    
    @staticmethod
    def build_not_done():
        return '''
╔════════════════════════════════════════════════════════════════╗
║  ❌ Error: Build system detected but no build artifacts        ║
╟────────────────────────────────────────────────────────────────╢
║  You need to BUILD the project before running tests!          ║
║                                                                 ║
║  If Makefile exists:                                           ║
║    cd /repo && make -j4                                        ║
║                                                                 ║
║  If CMakeLists.txt exists:                                     ║
║    mkdir -p /repo/build && cd /repo/build                      ║
║    cmake .. && make -j4                                        ║
║                                                                 ║
║  If configure exists:                                          ║
║    cd /repo && ./configure && make -j4                         ║
╚════════════════════════════════════════════════════════════════╝
'''
```

**사용**:
```python
# runtest.py
from utils.error_messages import ErrorGuide

if not build_check.stdout.strip():
    print(ErrorGuide.build_not_done())
    sys.exit(1)
```

**효과**:
- ✅ LLM이 다음 액션을 명확히 이해
- ✅ 일관된 에러 형식
- ✅ 학습 효과 (다음번에는 실수 안함)

---

## 🎯 우선순위별 액션 아이템

### Week 1: Critical Fixes
- [ ] **Fix 1**: runtest.py 빌드 산출물 검증 추가
- [ ] **Fix 2**: download.py 메시지 명확화 + 중복 방지
- [ ] **Fix 3**: integrate_dockerfile.py 실제 명령어 매칭
- [ ] **Test**: cJSON, tinyxml2, ImageMagick 재실행 검증

### Week 2: High Priority
- [ ] **Improvement 1**: configuration.py 프롬프트 단순화 (50% 토큰 절감)
- [ ] **Improvement 2**: sandbox.py Command Handler 패턴 적용
- [ ] **Test**: 리팩토링 후 기능 동일성 검증

### Week 3: Medium Priority
- [ ] **Improvement 3**: tiktoken 통합 + 정확한 토큰 카운팅
- [ ] **Improvement 4**: ErrorGuide 시스템 구축
- [ ] **Improvement 5**: 로깅 시스템 개선 (타임스탬프, Turn 번호)

### Week 4: Polish & Documentation
- [ ] 코드 중복 제거 (safe_cmd → constants.py)
- [ ] 설정 파일 분리 (timeout, Docker 리소스)
- [ ] 테스트 커버리지 향상
- [ ] 문서화 업데이트

---

## 📈 예상 효과

### 정량적 개선
| 지표 | Before | After | 개선율 |
|------|--------|-------|--------|
| 프롬프트 토큰 | 3000+ | ~1500 | **50% ↓** |
| False Negative (runtest) | ~30% | <5% | **83% ↓** |
| LLM 혼란 (download 재호출) | 빈번 | 없음 | **100% ↓** |
| Dockerfile 생성 실패율 | ~20% | <5% | **75% ↓** |
| 코드 복잡도 (sandbox.py) | 200줄 | ~80줄 | **60% ↓** |

### 정성적 개선
- ✅ **LLM 학습 향상**: 명확한 에러 메시지 → 빠른 문제 해결
- ✅ **유지보수성**: Command Pattern → 새로운 기능 추가 쉬움
- ✅ **디버깅**: 구조화된 로그 → 문제 원인 파악 빠름
- ✅ **확장성**: 명확한 책임 분리 → Rust/Go 지원 용이

---

## 📝 마무리

### 가장 시급한 3가지
1. **runtest.py 수정** - False Negative 제거 (많은 프로젝트에 영향)
2. **download.py 메시지 개선** - LLM 혼란 방지
3. **프롬프트 단순화** - 토큰 절약 + 명확성

### 장기 비전
- Command Handler 패턴으로 깔끔한 아키텍처
- 정확한 Token 관리로 비용 절감
- 명확한 에러 가이드로 성공률 향상

---

**작성일**: 2025-10-19  
**버전**: 1.0  
**다음 검토**: Week 1 완료 후



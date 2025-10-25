# ARVO2.0 경로 흐름 완전 분석

## 📍 1. 실행 시작점: main.py

### 명령어 실행
```bash
python3 build_agent/main.py <full_name> <sha> <root_path>
# 예: python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases
```

### root_path 계산 (main.py Line 208-215)
```python
root_path = args.root_path  # 예: "./10_Cases"

# 절대 경로로 변환
if not os.path.isabs(root_path):
    root_path = os.path.abspath(root_path)
    # → /root/Git/ARVO2.0/10_Cases

# build_agent 디렉토리 추가
if not root_path.endswith('build_agent'):
    root_path = os.path.join(root_path, 'build_agent')
    # → /root/Git/ARVO2.0/10_Cases/build_agent
```

### output_root 계산 (Line 220)
```python
output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
# 환경변수 없으면 root_path 사용
# → /root/Git/ARVO2.0/10_Cases/build_agent
```

---

## 📦 2. 레포지토리 클론/재사용 결정: download_repo()

### 함수 호출 (main.py Line 261)
```python
download_repo(root_path, full_name, sha)
# root_path: /root/Git/ARVO2.0/10_Cases/build_agent
# full_name: FFmpeg/FFmpeg
# sha: HEAD
```

### 로컬 레포 경로 계산 (main.py Line 74-79)
```python
def download_repo(root_path, full_name, sha):
    author_name = full_name.split('/')[0]  # FFmpeg
    repo_name = full_name.split('/')[1]    # FFmpeg
    
    # 최종 레포 경로
    repo_path = f'{root_path}/utils/repo/{author_name}/{repo_name}/repo'
    # → /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo
```

### 클론 vs 재사용 판단 (Line 90-147)
```python
# 1. 레포가 이미 존재하는가?
if os.path.exists(f'{repo_path}/.git'):
    print(f"🔄 Repository {full_name} already exists...")
    
    # 2. 현재 커밋이 타겟 커밋인가?
    current_commit = subprocess.run('git rev-parse HEAD', cwd=repo_path, ...)
    
    if current_commit.startswith(sha):
        print(f"✅ Already at commit {sha[:8]}, skipping...")
        # → 아무것도 안함 (재사용)
    else:
        print(f"📥 Fetching latest changes...")
        subprocess.run('git fetch --all', cwd=repo_path, ...)
        subprocess.run(f'git checkout {sha}', cwd=repo_path, ...)
        # → 기존 레포 업데이트

else:
    # 3. 레포가 없으면 새로 클론
    download_cmd = f"git clone https://github.com/{full_name}.git"
    subprocess.run(download_cmd, 
                   cwd=f'{root_path}/utils/repo/{author_name}', ...)
    # → /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/
    #    에서 클론 실행
    #    결과: .../utils/repo/FFmpeg/FFmpeg/ 생성
    
    move_files_to_repo(f'{root_path}/utils/repo/{author_name}/{repo_name}')
    # → FFmpeg 내부 파일들을 repo/ 서브디렉토리로 이동
    #    최종: .../utils/repo/FFmpeg/FFmpeg/repo/
```

### 디렉토리 구조
```
/root/Git/ARVO2.0/10_Cases/build_agent/
├── utils/
│   └── repo/
│       └── FFmpeg/
│           └── FFmpeg/
│               ├── Dockerfile          (sandbox가 생성)
│               ├── sha.txt             (target SHA 저장)
│               └── repo/               (실제 소스코드)
│                   ├── .git/
│                   ├── configure
│                   ├── Makefile
│                   └── ...
```

---

## 🐳 3. 샌드박스 컨테이너 시작: Sandbox.start_container()

### 샌드박스 생성 (main.py Line 266)
```python
configuration_sandbox = Sandbox(
    "gcr.io/oss-fuzz-base/base-builder",  # 베이스 이미지
    full_name,                              # FFmpeg/FFmpeg
    root_path                               # /root/Git/ARVO2.0/10_Cases/build_agent
)
```

### Sandbox.__init__ (sandbox.py Line 69-76)
```python
def __init__(self, namespace, repo_full_name, root_path):
    self.namespace = namespace      # gcr.io/oss-fuzz-base/base-builder
    self.full_name = repo_full_name # FFmpeg/FFmpeg
    self.root_path = root_path      # /root/Git/ARVO2.0/10_Cases/build_agent
```

### 컨테이너로 복사 (sandbox.py Line 184-226) - 수정 후
```python
def start_container(self, base_image=False):
    # 컨테이너 시작
    self.container = self.client.containers.run(...)
    
    # ✅ 수정됨: self.root_path 사용
    project_directory = self.root_path
    # → /root/Git/ARVO2.0/10_Cases/build_agent
    
    # 1. tools 복사
    cmd = f"chmod -R 777 {project_directory}/tools && \
           docker cp {project_directory}/tools {self.container.name}:/home"
    # → /root/Git/ARVO2.0/10_Cases/build_agent/tools → 컨테이너:/home/tools
    
    # 2. repo 복사
    cmd = f"docker cp {project_directory}/utils/repo/{self.full_name}/repo \
           {self.container.name}:/"
    # → /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo
    #    → 컨테이너:/repo
```

### 컨테이너 내부 구조
```
컨테이너 내부:
/
├── repo/               (호스트에서 복사됨)
│   ├── .git/
│   ├── configure
│   ├── Makefile
│   └── ...
├── home/
│   └── tools/          (호스트에서 복사됨)
│       ├── runtest.py
│       ├── apt_download.py
│       └── ...
└── src/                (베이스 이미지에 포함)
    ├── aflplusplus/
    ├── fuzztest/
    └── ...
```

---

## 🔨 4. Agent 실행 및 명령 기록

### Agent 실행 (main.py Line 268-269)
```python
configuration_agent = Configuration(sandbox, image_name, full_name, root_path, 100)
msg, outer_commands = configuration_agent.run(...)
```

Agent가 실행한 명령들이 `sandbox.commands` 리스트에 저장됩니다.

---

## 📄 5. Dockerfile 생성: integrate_dockerfile()

### 호출 (main.py Line 278)
```python
integrate_dockerfile(f'{output_root}/output/{full_name}')
# → /root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg
```

### 경로 계산 (integrate_dockerfile.py Line 343-366)
```python
def integrate_dockerfile(root_path):
    # root_path: /root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg
    
    author_name = root_path.split('/')[-2]  # FFmpeg
    repo_name = root_path.split('/')[-1]    # FFmpeg
    
    # COPY 경로 생성 (빌드 컨텍스트 기준 상대 경로)
    copy_repo_st = f'COPY utils/repo/{author_name}/{repo_name}/repo /repo'
    # → COPY utils/repo/FFmpeg/FFmpeg/repo /repo
    
    # SHA 읽기
    with open(f'{root_path}/sha.txt', 'r') as r1:
        sha = r1.read().strip()
    
    checkout_st = f'RUN cd /repo && git checkout {sha}'
```

### 생성된 Dockerfile (integrate_dockerfile.py Line 399-409)
```dockerfile
FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/FFmpeg/FFmpeg/repo /repo        ← 상대 경로!
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN mkdir -p /src/fuzztest/build               ← inner_commands.json에서 변환
RUN cd /src/fuzztest/build && cmake .. -DCMAKE_BUILD_TYPE=Release
RUN cd /src/fuzztest/build && make -j4
```

### Dockerfile 저장 위치
```
/root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg/Dockerfile
```

---

## 🏗️ 6. Dockerfile 빌드 검증: verify_dockerfile()

### 빌드 명령 (main.py Line 300-303)
```python
# 빌드 컨텍스트 설정
project_root = output_root  
# → /root/Git/ARVO2.0/10_Cases/build_agent

# Docker build 명령
build_cmd = ["docker", "build", 
             "-f", dockerfile_path,              # Dockerfile 절대 경로
             "-t", test_image, 
             project_root]                        # 빌드 컨텍스트
```

### 실제 실행되는 명령
```bash
docker build \
  -f /root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg/Dockerfile \
  -t arvo_test_ffmpeg_ffmpeg_1729737600 \
  /root/Git/ARVO2.0/10_Cases/build_agent
```

### 빌드 컨텍스트 구조
```
빌드 컨텍스트: /root/Git/ARVO2.0/10_Cases/build_agent/
│
├── Dockerfile에서 참조:
│   COPY utils/repo/FFmpeg/FFmpeg/repo /repo
│   → 빌드 컨텍스트 기준 상대 경로
│   → /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo
│
└── 실제 파일 위치:
    utils/
    └── repo/
        └── FFmpeg/
            └── FFmpeg/
                └── repo/     ← 여기서 복사
```

---

## 🔍 7. 경로 계산 요약

### 경로별 계산 기준

| 경로 변수 | 계산 기준 | 예시 값 |
|-----------|-----------|---------|
| **args.root_path** | 사용자 입력 | `./10_Cases` |
| **root_path** | `abspath(args.root_path) + /build_agent` | `/root/Git/ARVO2.0/10_Cases/build_agent` |
| **output_root** | `REPO2RUN_OUTPUT_ROOT` 환경변수 또는 `root_path` | `/root/Git/ARVO2.0/10_Cases/build_agent` |
| **repo_path** | `root_path + /utils/repo/{author}/{repo}/repo` | `/root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo` |
| **project_directory** (수정 전) | `dirname(dirname(__file__))` ❌ | `/root/Git/ARVO2.0/build_agent` (고정) |
| **project_directory** (수정 후) | `self.root_path` ✅ | `/root/Git/ARVO2.0/10_Cases/build_agent` |
| **dockerfile_path** | `output_root + /output/{full_name}/Dockerfile` | `/root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg/Dockerfile` |
| **build context** | `output_root` (= `root_path`) | `/root/Git/ARVO2.0/10_Cases/build_agent` |

---

## 🐛 8. FFmpeg 문제 원인 (수정 전)

### 문제의 경로 계산
```python
# sandbox.py Line 217-219 (수정 전)
current_file_path = os.path.abspath(__file__)  
# → /root/Git/ARVO2.0/build_agent/utils/sandbox.py

current_directory = os.path.dirname(current_file_path)
# → /root/Git/ARVO2.0/build_agent/utils

project_directory = os.path.dirname(current_directory)
# → /root/Git/ARVO2.0/build_agent  ❌ 항상 고정!
```

### 결과
```bash
docker cp /root/Git/ARVO2.0/build_agent/utils/repo/FFmpeg/FFmpeg/repo ...
# 실제 파일: /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo
# → 파일을 찾을 수 없음! (docker cp 실패)
```

### Agent의 대응
1. `ls /repo` → 빈 디렉토리
2. "It seems the `/repo` directory is not present"
3. `/src` 디렉토리 탐색
4. `/src/fuzztest` 발견 및 빌드 시도

---

## ✅ 9. 수정 내용

### sandbox.py Line 218 (수정 후)
```python
# Use self.root_path instead of calculating from __file__
project_directory = self.root_path  ✅
# → main.py에서 전달받은 root_path 사용
# → /root/Git/ARVO2.0/10_Cases/build_agent
```

### 효과
```bash
docker cp /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo ...
# → 올바른 경로! ✅
```

---

## 📌 10. 핵심 포인트

### 1. 클론 vs 재사용
- **판단 기준**: `{root_path}/utils/repo/{author}/{repo}/repo/.git` 존재 여부
- **재사용 조건**: 기존 레포 존재 + 이미 타겟 커밋에 위치
- **클론 조건**: 레포 없음 또는 다른 커밋에 위치

### 2. 경로 계산
- **절대 금지**: `__file__` 기반 경로 계산 (코드 위치에 종속)
- **올바른 방법**: `self.root_path` 사용 (main.py에서 전달)

### 3. Docker COPY
- **경로 타입**: 빌드 컨텍스트 기준 **상대 경로**
- **빌드 컨텍스트**: `root_path` (= `output_root`)
- **COPY 경로**: `utils/repo/{author}/{repo}/repo`

### 4. 컨테이너 복사
- **호스트 → 컨테이너**: `docker cp {호스트 절대 경로} {컨테이너}:{컨테이너 경로}`
- **tools**: `/home/tools`
- **repo**: `/repo`

---

## 🎯 11. 테스트 시나리오

### 정상 동작 확인
```bash
# 1. 10_Cases 디렉토리로 실행
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases

# 2. 경로 확인
ls -la /root/Git/ARVO2.0/10_Cases/build_agent/utils/repo/FFmpeg/FFmpeg/repo

# 3. Dockerfile 확인
cat /root/Git/ARVO2.0/10_Cases/build_agent/output/FFmpeg/FFmpeg/Dockerfile
# → COPY utils/repo/FFmpeg/FFmpeg/repo /repo 존재

# 4. 빌드 테스트
cd /root/Git/ARVO2.0/10_Cases/build_agent
docker build -f output/FFmpeg/FFmpeg/Dockerfile -t test .
```


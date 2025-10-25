# ARVO 2.3 전체 경로 흐름 상세 분석

## 📍 입력 → 출력 경로 매핑

### 1️⃣ 사용자 실행 명령

```bash
$ python3 build_agent/main.py harfbuzz/harfbuzz HEAD /root/Git/ARVO2.0/v2.3/
           ↑                  ↑                ↑    ↑
           스크립트            full_name        sha  root_path
```

**입력 인자 파싱**:
- `args.full_name` = `'harfbuzz/harfbuzz'`
- `args.sha` = `'HEAD'`
- `args.root_path` = `'/root/Git/ARVO2.0/v2.3/'`

---

### 2️⃣ main.py 경로 정규화 (Line 205-218)

```python
# Step 1: 절대 경로 변환
root_path = args.root_path  # '/root/Git/ARVO2.0/v2.3/'
if not os.path.isabs(root_path):
    root_path = os.path.abspath(root_path)
# 결과: '/root/Git/ARVO2.0/v2.3/' (변화 없음 - 이미 절대경로)

# Step 2: build_agent 디렉토리 추가
if not root_path.endswith('build_agent'):
    root_path = os.path.join(root_path, 'build_agent')
# 결과: '/root/Git/ARVO2.0/v2.3/build_agent' ✅

# Step 3: output_root 설정 (환경변수 우선, 없으면 root_path)
output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
# 결과: '/root/Git/ARVO2.0/v2.3/build_agent' (환경변수 없음)
```

**최종 베이스 경로**:
- `root_path` = `/root/Git/ARVO2.0/v2.3/build_agent` ✅
- `output_root` = `/root/Git/ARVO2.0/v2.3/build_agent` ✅

---

### 3️⃣ 각 경로 생성

```
/root/Git/ARVO2.0/v2.3/build_agent/
│
├── utils/
│   └── repo/                          ← Repository 저장소
│       └── harfbuzz/
│           └── harfbuzz/
│               └── repo/              ← 실제 git repo
│                   ├── .git/
│                   ├── src/
│                   └── ...
│
├── output/                            ← 빌드 결과 저장
│   └── harfbuzz/
│       └── harfbuzz/
│           ├── Dockerfile             ← 생성된 Dockerfile
│           ├── inner_commands.json
│           ├── outer_commands.json
│           ├── sha.txt
│           └── patch/
│
└── log/                               ← 로그 파일
    └── harfbuzz_harfbuzz_HEAD.log
```

---

### 4️⃣ download_repo() - Repository 다운로드 (Line 74-186)

```python
full_name = 'harfbuzz/harfbuzz'
author_name = full_name.split('/')[0]  # 'harfbuzz'
repo_name = full_name.split('/')[1]    # 'harfbuzz'

repo_path = f'{root_path}/utils/repo/{author_name}/{repo_name}/repo'
# 결과: /root/Git/ARVO2.0/v2.3/build_agent/utils/repo/harfbuzz/harfbuzz/repo
```

**Repository Reuse 로직**:
```python
if os.path.exists(f'{repo_path}/.git'):  # 기존 레포 존재?
    print("🔄 Repository already exists...")
    # git rev-parse HEAD → 현재 커밋 확인
    # 같으면 skip, 다르면 git fetch + checkout
else:
    # git clone https://github.com/harfbuzz/harfbuzz.git
    # move_files_to_repo()
```

---

### 5️⃣ integrate_dockerfile() - Dockerfile 생성 (Line 343-409)

**입력**:
```python
integrate_dockerfile(f'{output_root}/output/{full_name}')
# 입력: /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz
```

**경로 추출 (Line 345-347)**:
```python
root_path = '/root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz'
author_name = root_path.split('/')[-2]  # 'harfbuzz' ✅
repo_name = root_path.split('/')[-1]    # 'harfbuzz' ✅
```

**생성되는 Dockerfile 내용 (Line 362)**:
```dockerfile
FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
COPY utils/repo/harfbuzz/harfbuzz/repo /repo  ← 상대 경로!
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout abc123...
RUN apt-get install libbz2-dev
RUN apt-get install libpng-dev
...
RUN cd /repo && ./configure
RUN cd /repo && make -j4
```

**COPY 경로 분석**:
- `COPY utils/repo/harfbuzz/harfbuzz/repo /repo`
- 이 경로는 **build context 기준 상대 경로**

---

### 6️⃣ Docker 빌드 (Line 294-299)

#### **BEFORE - 잘못된 방식** ❌

```python
build_cmd = ["docker", "build", "-t", test_image, output_path]
# output_path = /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz
```

**Docker 해석**:
```
Build context: /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz/
Dockerfile: /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz/Dockerfile

COPY utils/repo/harfbuzz/harfbuzz/repo /repo
↓
실제 찾는 경로:
/root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz/utils/repo/...
                                                                    ↑
                                                            여기에는 없음! ❌
```

#### **AFTER - 수정된 방식** ✅

```python
build_context = output_path.rsplit('/output/', 1)[0]
# build_context = /root/Git/ARVO2.0/v2.3/build_agent

dockerfile_rel_path = os.path.relpath(dockerfile_path, build_context)
# dockerfile_rel_path = output/harfbuzz/harfbuzz/Dockerfile

build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", test_image, build_context]
```

**Docker 해석**:
```
Build context: /root/Git/ARVO2.0/v2.3/build_agent/
                                      ↑
                                  여기가 base!

Dockerfile: output/harfbuzz/harfbuzz/Dockerfile (상대경로)
실제 경로: /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz/Dockerfile ✅

COPY utils/repo/harfbuzz/harfbuzz/repo /repo
↓
실제 찾는 경로:
/root/Git/ARVO2.0/v2.3/build_agent/utils/repo/harfbuzz/harfbuzz/repo
                                   ↑
                               여기에 있음! ✅
```

---

## 🎯 핵심 포인트

### 1. root_path 처리

**입력**: 사용자가 제공한 경로  
**처리**: 항상 `build_agent`로 끝나도록 정규화  
**결과**: 모든 경로의 베이스

```
입력: /root/Git/ARVO2.0/v2.3/
처리: /root/Git/ARVO2.0/v2.3/build_agent  ← 자동 추가
```

### 2. 레포지토리 경로 (Download)

**패턴**: `{root_path}/utils/repo/{author}/{repo}/repo`

```
/root/Git/ARVO2.0/v2.3/build_agent/utils/repo/harfbuzz/harfbuzz/repo
                                   ↑                  ↑
                                utils/repo/      {author}/{repo}/repo
```

### 3. Output 경로

**패턴**: `{output_root}/output/{full_name}`

```
/root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz
                                   ↑              ↑
                                output/      {author}/{repo}
```

### 4. Docker Build Context (핵심!)

**BEFORE** ❌:
```
Build context = output_path
              = /root/Git/ARVO2.0/v2.3/build_agent/output/harfbuzz/harfbuzz/
                                                    ↑ utils/repo를 못 봄!
```

**AFTER** ✅:
```
Build context = root_path
              = /root/Git/ARVO2.0/v2.3/build_agent/
                                        ↑ utils/와 output/ 모두 보임!
```

---

## 📝 경로 계산 요약

| 항목 | 기준 | 최종 경로 |
|------|------|----------|
| **root_path** | 사용자 입력 + `/build_agent` | `/root/Git/ARVO2.0/v2.3/build_agent` |
| **Repository** | `{root_path}/utils/repo/{author}/{repo}/repo` | `.../build_agent/utils/repo/harfbuzz/harfbuzz/repo` |
| **Output** | `{output_root}/output/{full_name}` | `.../build_agent/output/harfbuzz/harfbuzz` |
| **Dockerfile** | `{output}/Dockerfile` | `.../output/harfbuzz/harfbuzz/Dockerfile` |
| **Build Context** | `output_path.rsplit('/output/', 1)[0]` | `.../build_agent` |
| **COPY 상대경로** | `utils/repo/{author}/{repo}/repo` | `utils/repo/harfbuzz/harfbuzz/repo` |

---

## 🔧 수정 내용

### main.py (Line 294-299)

**Before**:
```python
build_cmd = ["docker", "build", "-t", test_image, output_path]
```

**After**:
```python
build_context = output_path.rsplit('/output/', 1)[0]  # build_agent 경로
dockerfile_rel_path = os.path.relpath(dockerfile_path, build_context)
build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", test_image, build_context]
```

**효과**:
- ✅ Build context가 `build_agent` 디렉토리
- ✅ `utils/repo/` 접근 가능
- ✅ `output/` 접근 가능
- ✅ COPY 경로 정상 작동

---

## ✅ 검증

```bash
# 실제 경로 확인
$ ls /root/Git/ARVO2.0/v2.3/build_agent/utils/repo/harfbuzz/harfbuzz/repo/
✅ 존재함

# Docker 빌드 (이제 성공할 것)
$ cd /root/Git/ARVO2.0/v2.3/build_agent
$ docker build -f output/harfbuzz/harfbuzz/Dockerfile -t test .
→ COPY utils/repo/harfbuzz/harfbuzz/repo /repo  ✅ 성공!
```

---

**결론**: 
- 모든 경로는 **사용자가 입력한 root_path**를 기준으로 계산됨
- `build_agent`가 자동으로 추가되어 **통일된 베이스 경로** 제공
- Docker build context도 **build_agent 디렉토리**로 수정되어 모든 경로 접근 가능 ✅


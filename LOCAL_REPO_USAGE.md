# 로컬 레포지토리 사용 가이드

## 🎯 개요

이제 ARVO2.0은 두 가지 모드로 레포지토리를 가져올 수 있습니다:

1. **GitHub 클론 모드** (기본): 네트워크를 통해 GitHub에서 클론
2. **로컬 복사 모드** (NEW): 이미 로컬에 있는 레포를 복사

---

## 📝 사용법

### 1️⃣ GitHub 클론 모드 (기존 방식)

```bash
python3 build_agent/main.py <full_name> <sha> <root_path>
```

**예시:**
```bash
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases
```

**동작:**
- `{root_path}/utils/repo/FFmpeg/FFmpeg/repo/.git` 존재 확인
- **있으면**: git fetch + checkout으로 업데이트
- **없으면**: GitHub에서 git clone

---

### 2️⃣ 로컬 복사 모드 (NEW)

```bash
python3 build_agent/main.py <full_name> <sha> <root_path> --local-repo <local_repo_path>
```

**예시:**
```bash
# 로컬에 이미 클론된 FFmpeg 사용
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases \
  --local-repo /mnt/repos/FFmpeg
```

**동작:**
1. `<local_repo_path>` 존재 및 유효성 검증
2. 기존 타겟 디렉토리 삭제 (있으면)
3. `cp -r` 로 전체 레포 복사 (`.git` 포함)
4. 지정된 `<sha>`로 checkout

---

## ✨ 장점

### 로컬 복사 모드를 사용하면:

1. **🚀 빠른 속도**: 네트워크 오버헤드 없음
2. **📦 오프라인 작업**: 인터넷 연결 불필요
3. **🔄 재사용성**: 여러 실험에서 같은 레포 재사용 가능
4. **💾 디스크 효율**: 로컬에 이미 있는 레포 활용
5. **🛠️ 수정 레포 사용**: 로컬에서 수정한 버전 테스트 가능

---

## 📂 디렉토리 구조

### 로컬 복사 전
```
/mnt/repos/FFmpeg/          ← 로컬에 이미 클론된 레포
├── .git/
├── configure
├── Makefile
└── ...
```

### 로컬 복사 후
```
/root/Git/ARVO2.0/10_Cases/build_agent/
└── utils/
    └── repo/
        └── FFmpeg/
            └── FFmpeg/
                └── repo/           ← 복사된 레포
                    ├── .git/       ← 복사됨
                    ├── configure
                    ├── Makefile
                    └── ...
```

---

## 🔍 검증 과정

### 로컬 레포 경로 제공 시 검증:

1. **경로 존재 확인**:
   ```python
   if not os.path.exists(local_repo_path):
       raise Exception("Local repo path does not exist")
   ```

2. **Git 레포 확인**:
   ```python
   if not os.path.exists(f'{local_repo_path}/.git'):
       raise Exception("Path is not a git repository")
   ```

3. **복사 실행**:
   ```bash
   cp -r /mnt/repos/FFmpeg /root/.../utils/repo/FFmpeg/FFmpeg/repo
   ```

4. **Checkout**:
   ```bash
   cd /root/.../utils/repo/FFmpeg/FFmpeg/repo
   git checkout HEAD
   ```

---

## 💡 사용 시나리오

### Scenario 1: 대용량 레포 반복 실험
```bash
# 1. 처음 한 번만 클론
git clone https://github.com/FFmpeg/FFmpeg.git /mnt/repos/FFmpeg

# 2. 여러 실험에서 재사용
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./experiment1 \
  --local-repo /mnt/repos/FFmpeg

python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./experiment2 \
  --local-repo /mnt/repos/FFmpeg
```

### Scenario 2: 수정된 레포 테스트
```bash
# 1. 로컬에서 수정
cd /mnt/repos/FFmpeg
# ... 코드 수정 ...
git commit -am "Test fix"

# 2. 수정된 버전 테스트
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./test_fix \
  --local-repo /mnt/repos/FFmpeg
```

### Scenario 3: 오프라인 환경
```bash
# 온라인에서 준비
git clone https://github.com/curl/curl.git /backup/curl

# 오프라인에서 사용
python3 build_agent/main.py curl/curl HEAD ./offline_test \
  --local-repo /backup/curl
```

---

## ⚠️ 주의사항

### 1. 원본 레포는 보존됨
- `cp -r` 사용 (NOT `mv`)
- 원본 레포는 변경되지 않음
- 복사본만 타겟 디렉토리에 생성

### 2. `.git` 디렉토리 포함
- 전체 git history 복사
- checkout 가능
- git 명령어 사용 가능

### 3. 디스크 용량
- 레포가 두 벌 존재 (원본 + 복사본)
- 대용량 레포 주의

### 4. 경로는 절대 경로 권장
```bash
# ✅ Good
--local-repo /mnt/repos/FFmpeg

# ⚠️ 상대 경로도 가능하지만 주의
--local-repo ../my-repos/FFmpeg
```

---

## 🧪 테스트

### 간단한 테스트
```bash
# 1. 로컬에 테스트 레포 준비
git clone https://github.com/curl/curl.git /tmp/test-curl

# 2. 로컬 복사 모드로 실행
python3 build_agent/main.py curl/curl HEAD ./10_Cases \
  --local-repo /tmp/test-curl

# 3. 복사 확인
ls -la 10_Cases/build_agent/utils/repo/curl/curl/repo/.git
```

### 비교 테스트
```bash
# 클론 모드 (네트워크 사용)
time python3 build_agent/main.py curl/curl HEAD ./test1

# 로컬 복사 모드 (네트워크 불필요)
time python3 build_agent/main.py curl/curl HEAD ./test2 \
  --local-repo /tmp/test-curl
```

---

## 🔧 트러블슈팅

### 에러: "Local repo path does not exist"
```bash
# 경로 확인
ls -la /path/to/repo

# 절대 경로 사용
--local-repo $(realpath /path/to/repo)
```

### 에러: "Path is not a git repository"
```bash
# .git 디렉토리 확인
ls -la /path/to/repo/.git

# git status 테스트
cd /path/to/repo && git status
```

### 에러: "Failed to checkout"
```bash
# SHA가 로컬 레포에 존재하는지 확인
cd /path/to/repo
git log | grep <sha>

# 필요시 fetch
git fetch origin
```

---

## 📊 성능 비교

| 모드 | FFmpeg (600MB) | curl (200MB) | 네트워크 필요 |
|------|----------------|--------------|---------------|
| **GitHub 클론** | ~30초 | ~10초 | ✅ 필요 |
| **로컬 복사** | ~5초 | ~2초 | ❌ 불필요 |

---

## 🎓 Best Practices

1. **대용량 레포**: 로컬 복사 모드 사용
2. **반복 실험**: 로컬 복사 모드로 시간 절약
3. **네트워크 불안정**: 로컬 복사 모드로 안정성 확보
4. **일회성 테스트**: GitHub 클론 모드 (간단)
5. **CI/CD**: 로컬 복사 모드로 빌드 시간 단축

---

## 🔄 마이그레이션 가이드

### 기존 스크립트 업데이트

**Before:**
```bash
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases
```

**After (로컬 레포 사용):**
```bash
# 1회만 클론
git clone https://github.com/FFmpeg/FFmpeg.git /opt/repos/FFmpeg

# 스크립트 업데이트
python3 build_agent/main.py FFmpeg/FFmpeg HEAD ./10_Cases \
  --local-repo /opt/repos/FFmpeg
```

**호환성:**
- `--local-repo` 옵션은 **optional**
- 기존 스크립트는 그대로 작동 ✅


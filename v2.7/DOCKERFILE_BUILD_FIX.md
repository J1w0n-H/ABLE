# Dockerfile 빌드 실패 원인 및 해결

**날짜**: 2024-10-26  
**문제**: Dockerfile 검증 단계에서 build context 경로 오류

---

## 🔴 문제

### 에러 메시지
```
❌ unable to prepare context: unable to evaluate symlinks in Dockerfile path: 
   lstat /root/Git/ARVO2.0/output: no such file or directory
```

### 발생 시점
- `runtest` 성공 후
- `verify_dockerfile()` 실행 중
- Docker build 시도 시

---

## 🔍 근본 원인

### Dockerfile 내용 (integrate_dockerfile.py Line 362)
```dockerfile
COPY utils/repo/harfbuzz/harfbuzz/repo /repo
```

### Docker build 실행 (main.py Line 299)
```python
build_context = output_path.rsplit('/output/', 1)[0]
build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", test_image, build_context]
```

### 문제 분석
```
output_path:    /root/Git/ARVO2.0/v2.6/build_agent/output/harfbuzz/harfbuzz
                                      ^^^^^^^^^^^^^^^^
rsplit('/output/', 1)[0]:             /root/Git/ARVO2.0/v2.6/build_agent
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
build_context:  /root/Git/ARVO2.0/v2.6/build_agent

Docker COPY 찾는 위치:
  /root/Git/ARVO2.0/v2.6/build_agent/utils/repo/harfbuzz/harfbuzz/repo
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  → 존재하지 않음! ❌

실제 repo 위치:
  /root/Git/ARVO2.0/build_agent/utils/repo/harfbuzz/harfbuzz/repo
  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  → 여기 있음! ✅
```

### 근본 원인
- `build_context` 계산이 **output_root (v2.6)** 기준
- 실제 repo는 **project root (/root/Git/ARVO2.0/build_agent)** 에 있음
- v2.6, v2.7 같은 버전 디렉토리는 **결과 저장용**이지 코드 위치가 아님!

---

## ✅ 해결책

### Option A: build_context를 project root로 고정
```python
# main.py Line 295-297
# BEFORE:
build_context = output_path.rsplit('/output/', 1)[0]

# AFTER:
# Build context must be /root/Git/ARVO2.0/build_agent (where utils/repo/ is)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
build_context = os.path.join(project_root, 'build_agent')
```

### Option B: 상대 경로 계산 개선
```python
# main.py Line 295-297
# Build context is always build_agent directory (where utils/repo lives)
if 'build_agent' in output_path:
    # Extract everything before the version directory
    parts = output_path.split('/')
    # Find ARVO2.0 index
    arvo_idx = parts.index('ARVO2.0')
    build_context = '/'.join(parts[:arvo_idx+1]) + '/build_agent'
else:
    build_context = output_path.rsplit('/output/', 1)[0]
```

### Option C: 환경 변수 사용
```python
# main.py 시작 부분
BUILD_AGENT_ROOT = os.path.abspath(os.path.dirname(__file__))

# verify_dockerfile 함수
build_context = BUILD_AGENT_ROOT
```

---

## 🎯 권장 해결책: Option C

**이유**:
1. **간단**: 환경 변수 사용
2. **명확**: build_agent 디렉토리 명시
3. **안정**: 경로 계산 오류 없음
4. **유지보수**: 이해하기 쉬움

**구현**:
```python
# main.py 최상단 (imports 이후)
BUILD_AGENT_ROOT = os.path.abspath(os.path.dirname(__file__))

# verify_dockerfile 함수 (Line 295-297)
# Build context must be build_agent directory to access utils/repo/
build_context = BUILD_AGENT_ROOT
dockerfile_rel_path = os.path.relpath(dockerfile_path, build_context)
build_cmd = ["docker", "build", "-f", dockerfile_rel_path, "-t", test_image, build_context]
```

---

## 📊 영향

### 현재 상황
- ❌ Dockerfile 검증 실패
- ✅ runtest는 성공 (빌드 자체는 OK)
- ❌ 생성된 Dockerfile은 사용 불가

### 수정 후
- ✅ Dockerfile 검증 성공
- ✅ 생성된 Dockerfile 사용 가능
- ✅ 재현 가능한 빌드

---

## 🚀 v2.7 포함 여부

**권장**: **포함하지 않음**

**이유**:
1. v2.7의 핵심은 **split 제거** (One-Step 수정)
2. Dockerfile 검증은 **별도 기능** (optional)
3. runtest 성공하면 빌드는 정상
4. 별도 PR로 분리 가능

**대안**:
- v2.7 테스트 완료 후
- v2.8에서 Dockerfile 수정 포함
- 또는 hotfix로 별도 배포


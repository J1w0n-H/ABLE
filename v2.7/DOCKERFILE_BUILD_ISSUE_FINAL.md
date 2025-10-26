# Dockerfile 빌드 실패 - 최종 원인 분석

**날짜**: 2024-10-26  
**문제**: `unable to prepare context: lstat /root/Git/ARVO2.0/output: no such file or directory`

---

## 🔴 근본 원인

### 환경 변수 설정 문제

**에러 경로**:
```
lstat /root/Git/ARVO2.0/output
      ^^^^^^^^^^^^^^^^^^^^^^^^
      v2.6이 빠진 경로!
```

**예상 경로**:
```
/root/Git/ARVO2.0/v2.6/build_agent/output
```

---

## 🔍 상세 분석

### main.py 경로 설정 로직

#### 1. root_path 설정 (Line 206-213)
```python
root_path = args.root_path  # 배치 스크립트에서: "/root/Git/ARVO2.0/v2.6/"

if not os.path.isabs(root_path):
    root_path = os.path.abspath(root_path)

# root_path should point to build_agent directory
if not root_path.endswith('build_agent'):
    root_path = os.path.join(root_path, 'build_agent')

# 결과: root_path = "/root/Git/ARVO2.0/v2.6/build_agent"
```

#### 2. output_root 설정 (Line 218)
```python
output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
```

**문제**: 환경 변수 `REPO2RUN_OUTPUT_ROOT`가 설정되어 있으면 root_path 무시!

---

## 💥 실제 발생 상황

### 시나리오

1. **배치 스크립트 실행**:
   ```bash
   ROOT_PATH="/root/Git/ARVO2.0/v2.6/"
   python3 main.py "$full_name" "$sha" "$ROOT_PATH"
   ```

2. **환경 변수 존재** (이전 테스트에서 설정됨):
   ```bash
   export REPO2RUN_OUTPUT_ROOT="/root/Git/ARVO2.0"
   ```

3. **main.py Line 218**:
   ```python
   output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)
   # 환경 변수가 우선!
   # output_root = "/root/Git/ARVO2.0"  ← 여기!
   ```

4. **verify_dockerfile (Line 341)**:
   ```python
   verify_dockerfile(
       f'{output_root}/output/{full_name}',  
       # = /root/Git/ARVO2.0/output/harfbuzz/harfbuzz
       full_name
   )
   ```

5. **build_context 계산 (Line 297)**:
   ```python
   build_context = output_path.rsplit('/output/', 1)[0]
   # = /root/Git/ARVO2.0
   ```

6. **Docker build 실행**:
   ```bash
   docker build -f output/harfbuzz/harfbuzz/Dockerfile \
                -t test \
                /root/Git/ARVO2.0
   ```
   
   - Docker가 `/root/Git/ARVO2.0/output/...` 찾으려 함
   - **이 디렉토리 없음!** ❌
   - 실제 repo는 `/root/Git/ARVO2.0/v2.6/build_agent/utils/repo/...`

---

## ✅ 해결책

### Option 1: 환경 변수 제거 (즉시)
```bash
unset REPO2RUN_OUTPUT_ROOT
```

**장점**: 즉시 해결  
**단점**: 매번 확인 필요

---

### Option 2: 배치 스크립트 수정 (권장)
```bash
#!/bin/bash
# v2.7 배치 테스트

# 환경 변수 명시적으로 제거
unset REPO2RUN_OUTPUT_ROOT

ROOT_PATH="/root/Git/ARVO2.0/v2.7/"
cd /root/Git/ARVO2.0/build_agent
python3 main.py "$full_name" "$sha" "$ROOT_PATH"
```

**장점**: 명시적, 안전  
**단점**: 없음

---

### Option 3: main.py 로직 개선 (근본)
```python
# Line 218
# BEFORE:
output_root = os.getenv('REPO2RUN_OUTPUT_ROOT', root_path)

# AFTER:
# Only use environment variable if explicitly set AND valid
env_output_root = os.getenv('REPO2RUN_OUTPUT_ROOT')
if env_output_root and os.path.isabs(env_output_root):
    output_root = env_output_root
    print(f"⚠️  Using REPO2RUN_OUTPUT_ROOT: {output_root}")
else:
    output_root = root_path
```

**장점**: 근본 해결, 명시적  
**단점**: 코드 변경 필요

---

## 🎯 권장 조치

### 즉시 조치
```bash
# 현재 환경 확인
env | grep REPO2RUN

# 설정되어 있으면 제거
unset REPO2RUN_OUTPUT_ROOT

# 확인
env | grep REPO2RUN
```

### 장기 조치
- v2.7 배치 스크립트에 `unset` 추가
- 또는 v2.8에서 main.py 로직 개선

---

## 📊 영향

### 현재
- ✅ runtest 성공 (빌드는 정상)
- ❌ Dockerfile 검증 실패 (환경 변수 때문)
- ✅ 배치 테스트 결과는 유효 (실제 빌드 OK)

### 해결 후
- ✅ runtest 성공
- ✅ Dockerfile 검증 성공
- ✅ 재현 가능한 Dockerfile

---

## 🚀 v2.7 영향

**결론**: v2.7 테스트는 정상 진행 가능!

**이유**:
1. 환경 변수만 제거하면 OK
2. v2.7 핵심 (split 제거)과 무관
3. Dockerfile 검증은 optional 기능

**조치**:
```bash
unset REPO2RUN_OUTPUT_ROOT
./run_v2.7_batch.sh
```


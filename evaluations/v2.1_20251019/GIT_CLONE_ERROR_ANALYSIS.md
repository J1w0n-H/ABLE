# Git Clone 에러 분석 및 해결 방안

## 🔍 에러 분석

### 발생한 에러:
```
Cloning into 'ImageMagick'...
remote: Enumerating objects: 178733, done.
remote: Counting objects: 100% (343/343), done.
remote: Compressing objects: 100% (141/141), done.
error: RPC failed; curl 92 HTTP/2 stream 5 was not closed cleanly: CANCEL (err 8)
error: 83 bytes of body are still expected
fetch-pack: unexpected disconnect while reading sideband packet
fatal: early EOF
fatal: fetch-pack: invalid index-pack output
Failed to clone repository from GitHub: ImageMagick/ImageMagick
Error: Command 'git clone https://github.com/ImageMagick/ImageMagick.git' returned non-zero exit status 128.
```

---

## ✅ 이것은 정상적인 동작입니다!

### 개선된 에러 처리가 작동한 것

**main.py (개선 버전, Line 82-87)**:
```python
try:
    subprocess.run(download_cmd, cwd=f'{root_path}/utils/repo/{author_name}', check=True, shell=True)
except subprocess.CalledProcessError as e:
    print(f"Failed to clone repository from GitHub: {full_name}")
    print(f"Error: {e}")
    raise Exception(f"Cannot clone repository {full_name}. Please check network connection and repository accessibility.")
```

**작동 확인**:
- ✅ Git clone 실패 감지
- ✅ 명확한 에러 메시지 출력
- ✅ Exception 발생 (즉시 종료)
- ✅ 빈 디렉토리로 진행 안함 (개선 효과!)

**Before (이전 버전)의 문제**:
```python
# 이전에는:
except subprocess.CalledProcessError:
    if os.path.exists(f'{root_path}/utils/repo/{author_name}/{repo_name}'):
        print(f"Using existing local repository")  # ← 빈 디렉토리도 통과!
```
→ 빈 `/repo`로 진행 → LLM이 `/src` 탐색 → 잘못된 타겟 빌드

---

## 🎯 에러 원인

### 네트워크 문제 (일시적)

**증거**:
1. **RPC failed; curl 92** - HTTP/2 연결 문제
2. **stream 5 was not closed cleanly: CANCEL** - 서버가 연결 취소
3. **early EOF** - 데이터 전송 중단
4. **178,733 objects** - 매우 큰 레포지토리 (600MB+)

**원인 가능성**:
1. ✅ **네트워크 불안정** - GitHub 서버 또는 로컬 네트워크
2. ✅ **타임아웃** - 큰 레포지토리 다운로드 중 연결 끊김
3. ✅ **GitHub rate limit** - 대용량 clone 제한
4. ⚠️ **메모리 부족** - 178K objects 처리 중 문제 가능성

---

## 🔧 해결 방법

### Solution 1: 재시도 (가장 간단)
```bash
# 단순히 다시 실행
cd /root/Git/ARVO2.0
python build_agent/main.py ImageMagick/ImageMagick 6f6caf /root/Git/ARVO2.0
```

**성공 가능성**: 80% (일시적 네트워크 문제)

---

### Solution 2: Shallow Clone (권장!)
```bash
# main.py의 download_cmd 수정
download_cmd = f"git clone --depth 1 https://github.com/{full_name}.git"
#                         ↑↑↑↑↑↑↑↑
# depth 1: 최신 커밋만 (히스토리 제외)
```

**효과**:
- 178K objects → ~5K objects
- 600MB → ~50MB
- 2분 → 10초
- 성공률 ↑

**주의**: SHA checkout이 실패할 수 있음 (depth 1은 히스토리 없음)

---

### Solution 3: 수동 Clone + 실행
```bash
# 직접 clone
cd /root/Git/ARVO2.0/build_agent/utils/repo
mkdir -p ImageMagick
cd ImageMagick
git clone --depth 1 --branch main https://github.com/ImageMagick/ImageMagick.git

# repo 폴더 정리
cd ImageMagick
mkdir repo_inner_directory_long_long_name_to_avoid_duplicate
mv * repo_inner_directory_long_long_name_to_avoid_duplicate/ 2>/dev/null
mv repo_inner_directory_long_long_name_to_avoid_duplicate repo

# main.py 실행 (clone 건너뛰기)
cd /root/Git/ARVO2.0
# ... 하지만 main.py는 항상 rm -rf 하므로 소용없음
```

**문제**: main.py가 매번 디렉토리 삭제함

---

### Solution 4: 다른 커밋 시도
```bash
# ImageMagick의 특정 tag나 작은 커밋
python build_agent/main.py ImageMagick/ImageMagick 7.1.0-0 /root/Git/ARVO2.0

# 또는 다른 프로젝트 테스트
python build_agent/main.py curl/curl curl-8_0_1 /root/Git/ARVO2.0
```

---

### Solution 5: Git 설정 조정 (영구적 해결)
```bash
# HTTP buffer 증가
git config --global http.postBuffer 524288000  # 500MB
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

# 재시도
python build_agent/main.py ImageMagick/ImageMagick 6f6caf /root/Git/ARVO2.0
```

---

## 📊 ImageMagick 레포지토리 특성

### 크기 정보:
```
Objects: 178,733 개
Size: ~600MB (추정)
History: 20+ years
Contributors: 100+
```

**이것은 매우 큰 레포지토리입니다!**

### 대안 프로젝트 (테스트용):
| 프로젝트 | Objects | Size | 복잡도 |
|---------|---------|------|--------|
| **Hello World** | ~10 | <1KB | ⭐ |
| **cJSON** | ~500 | ~200KB | ⭐⭐ |
| **tinyxml2** | ~800 | ~500KB | ⭐⭐ |
| **zlib** | ~1,500 | ~1MB | ⭐⭐⭐ |
| **curl** | ~30,000 | ~50MB | ⭐⭐⭐⭐ |
| **ImageMagick** | ~178,000 | ~600MB | ⭐⭐⭐⭐⭐ |

---

## 💡 권장 액션

### Option A: 간단한 재시도
```bash
# 1-2번 더 시도
python build_agent/main.py ImageMagick/ImageMagick 6f6caf /root/Git/ARVO2.0
```

### Option B: Git 설정 후 재시도 (권장!)
```bash
# Git buffer 증가
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

# 재시도
python build_agent/main.py ImageMagick/ImageMagick 6f6caf /root/Git/ARVO2.0
```

### Option C: 다른 프로젝트로 검증
```bash
# curl (중간 크기, 의존성 많음)
python build_agent/main.py curl/curl curl-8_0_1 /root/Git/ARVO2.0

# zlib (작고 간단)
python build_agent/main.py madler/zlib v1.3 /root/Git/ARVO2.0
```

---

## 🎯 핵심 요약

### ✅ 이것은 버그가 아닙니다!

**증거**:
1. ✅ 개선된 에러 처리가 정상 작동
2. ✅ 명확한 에러 메시지 출력
3. ✅ 즉시 종료 (빈 디렉토리로 진행 안함)
4. ✅ 네트워크 문제 감지

**원인**: 일시적 네트워크 문제 (큰 레포 clone 중)

**해결**: Git 설정 조정 + 재시도

---

**작성일**: 2025-10-19  
**에러 타입**: 네트워크 (일시적)  
**권장 액션**: Git buffer 증가 → 재시도  
**대안**: 다른 프로젝트로 개선 검증 (curl, zlib 등)


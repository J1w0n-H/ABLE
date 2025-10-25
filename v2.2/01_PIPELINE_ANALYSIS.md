# ARVO2.0 v2.2 - 파이프라인 분석

## 📋 전체 파이프라인 흐름

### Phase 1: 초기화 (main.py)
```
1. 인자 파싱 (full_name, sha, root_path)
2. 로깅 설정 (TeeOutput)
3. 타이머 시작 (2시간 제한)
4. 레포지토리 다운로드
   ├─ Git clone
   ├─ 폴더 정리 (repo/)
   └─ SHA checkout
```

### Phase 2: 빌드 환경 구성 (configuration.py)
```
5. Sandbox 생성
   ├─ Dockerfile 생성 (gcr.io/oss-fuzz-base/base-builder)
   ├─ Docker 이미지 빌드
   └─ 컨테이너 시작 + /repo 마운트

6. Configuration Agent 실행 (최대 100턴)
   ├─ LLM에게 프롬프트 전달
   └─ 반복:
       ├─ LLM 응답
       ├─ 명령어 추출 및 실행 (sandbox.execute)
       ├─ 결과 관찰
       └─ 성공 체크: "Congratulations!"
```

### Phase 3: 결과 저장 (integrate_dockerfile.py)
```
7. 컨테이너 중지
8. Dockerfile 생성
   ├─ inner_commands.json 읽기
   ├─ 성공한 명령어만 Dockerfile로 변환
   └─ 최종 Dockerfile 저장
```

---

## ❌ 발견된 문제점 (13개)

### 🔴 Critical (즉시 수정 필요)

#### 1. runtest.py - 빌드 산출물 검증 부족
- **문제**: Makefile 있으면 무조건 `make test` 실행
- **영향**: test 타겟 없으면 실패 (False Negative 30%)
- **근본 원인**: 빌드 여부를 확인하지 않음

#### 2. download.py - 무한 재시도 가능성
- **문제**: "Download all pending elements" - 모호한 설명
- **영향**: LLM이 download 반복 호출 (~40%)
- **근본 원인**: 한 번만 호출해야 한다는 것을 명시 안함

#### 3. integrate_dockerfile.py - 존재하지 않는 도구 체크
- **문제**: `run_make.py`, `apt_install.py` 체크 (실제로 없음)
- **영향**: apt_download.py가 Dockerfile에 그대로 → 빌드 실패
- **근본 원인**: Repo2Run에서 복사한 코드 (실제 패턴과 미스매치)

---

### 🟠 High Priority

#### 4. configuration.py - 프롬프트 과다 반복
- **문제**: 같은 내용 3번씩 반복 (18번 반복, ~1,200 토큰)
- **영향**: 토큰 낭비, LLM이 중요도 파악 어려움

#### 5. sandbox.py - execute() 메서드 복잡도
- **문제**: 200줄의 거대한 if-elif 체인
- **영향**: 테스트 어려움, 확장 어려움, 버그 위험

#### 6. runtest.py - 성공 마커 충돌
- **문제**: `# This is $runtest.py$` 마커가 성공 조건 방해
- **영향**: 무한 루프 (79% 턴 낭비)

---

### 🟡 Medium Priority

#### 7. Token 관리 - 부정확한 계산
- **문제**: `len(str(message))`로 토큰 계산 (실제 토큰과 다름)
- **영향**: 429 에러 가능성

#### 8. waiting_list/conflict_list - 복잡한 상태 관리
- **문제**: C 프로젝트에서 conflict_list 불필요 (Python용)
- **영향**: LLM 혼란

#### 9. 에러 메시지 - 액션 가이드 부족
- **문제**: "CMakeLists.txt found but not configured" (다음 할 일 불명확)
- **영향**: LLM이 헤맴

#### 10. 로깅 - 디버깅 정보 부족
- **문제**: 타임스탬프, Turn 번호 없음
- **영향**: 디버깅 어려움

---

### 🟢 Low Priority

#### 11. 코드 중복 - safe_cmd 리스트
- 2곳에 동일 리스트 정의

#### 12. 타이머 - 2시간 하드코딩
- 환경 변수로 변경 필요

#### 13. Docker 리소스 - 하드코딩
- mem_limit, cpuset_cpus 하드코딩

---

## 📈 예상 개선 효과

| 지표 | Before | After (목표) | 개선 |
|-----|--------|-------------|------|
| 평균 턴 수 | ~17턴 | ~5턴 | 65% ↓ |
| 성공률 | 70% | 95% | 36% ↑ |
| False Negative | 30% | <5% | 83% ↓ |
| 토큰 사용 | 100% | 60% | 40% ↓ |
| 비용 | $0.085 | $0.025 | 71% ↓ |

---

**상세 내용**: 
- 문제점 상세: `PIPELINE_ANALYSIS.md` (루트)
- 개선 방안: `02_IMPROVEMENTS.md`

**작성일**: 2025-10-19  
**버전**: 2.2




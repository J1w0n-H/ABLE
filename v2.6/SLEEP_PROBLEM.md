# sleep 0.5 처리 문제 (진짜 원인)

**당신의 지적**: "그거때문이 아니라 SLEEP을 제대로 처리못하는거아니야?"  
**답변**: **정확합니다!** && sleep 0.5 자체가 문제입니다!

---

## 🔴 문제 증거

### v2.5 로그 (Line 1366):
```
sed -n '20,60p' /repo/binutils/Makefile.am && sleep 0.5 [A]0;
                                                        ^^^^^
                                                        이상한 문자!
```

### 분석:
- `sed ... && sleep 0.5` 에코됨
- `[A]0;` = ANSI escape sequence? 프롬프트?
- 그 다음: **아무것도 없음!** (멈춤)
- returncode: 123

---

## 🔍 근본 원인

### 현재 방식 (sandbox.py Line 472):
```python
self.sandbox.shell.sendline(command + " && sleep 0.5")
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

### 타임라인:
```
Time 0.00s: sendline("sed ... && sleep 0.5")
Time 0.01s: Docker 에코 "sed ... && sleep 0.5"
Time 0.02s: sed 실행 시작
Time 0.05s: sed 완료 (출력 40줄)
Time 0.06s: sleep 0.5 시작 ← 여기서 문제!
Time 0.56s: sleep 완료
Time 0.57s: 프롬프트 "root@..." 출력
Time 0.58s: pexpect 매칭?
```

### 문제점:

#### 1. sleep 중 프롬프트가 이미 나타날 수 있음
```
sed 끝 (0.05s)
  ↓
프롬프트? (0.05s)  ← 너무 빨라!
  ↓
sleep 시작 (0.06s)
  ↓
pexpect: "프롬프트 못 찾음!" (0.06s)
```

#### 2. 터미널 escape sequence 간섭
```
sed 출력: "AUTOMAKE_OPTIONS = ...\r\n"
프롬프트: "root@container:/repo# "
sleep: (실행 중)
터미널: [A]0; ← cursor movement?
```

#### 3. pexpect 버퍼 타이밍
```
expect()가 호출될 때:
  - sed 출력: 이미 완료
  - sleep: 실행 중
  - 프롬프트: 아직 없음!
  
600초 대기 → TIMEOUT → exception → 123
```

---

## ✅ 해결책

### Option A: `;` 사용 (&&가 아닌) ⭐⭐

**변경:**
```python
# Before:
self.sandbox.shell.sendline(command + " && sleep 0.5")

# After:
self.sandbox.shell.sendline(command + " ; sleep 0.5")
                                      ^
```

**효과:**
- sed 실패해도 sleep 실행
- 프롬프트 반환 보장
- pexpect 매칭 성공

**장점:**
- 간단한 수정 (1글자!)
- 확실한 효과
- 부작용 없음

### Option B: echo 마커 ⭐

**변경:**
```python
# After:
marker = "__CMD_DONE__"
self.sandbox.shell.sendline(f"{command} && echo '{marker}'")
self.sandbox.shell.expect([marker], timeout=600)
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=10)
```

**효과:**
- 명령 완료 확실히 감지
- 프롬프트 안정적 대기

**단점:**
- 출력에 마커 포함됨 (제거 필요)
- 2번 expect 호출

### Option C: sleep 제거 + Python 대기

**변경:**
```python
# After:
self.sandbox.shell.sendline(command)
time.sleep(0.1)  # Python에서 대기
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

**효과:**
- 간단함
- sleep 문제 회피

**단점:**
- 출력 플러시 보장 약함

### Option D: 명령 후 true 추가

**변경:**
```python
# After:
self.sandbox.shell.sendline(f"{command} ; true")
self.sandbox.shell.expect([r'root@.*:.*# '], timeout=600)
```

**효과:**
- ; true가 항상 성공 (returncode 0)
- 프롬프트 확실히 반환

---

## 📊 비교

| 방안 | 복잡도 | 안정성 | 효과 |
|------|--------|--------|------|
| A: `;` 사용 | 낮음 | 높음 | ⭐⭐⭐ |
| B: echo 마커 | 중 | 매우높음 | ⭐⭐ |
| C: sleep 제거 | 낮음 | 중 | ⭐ |
| D: ; true | 낮음 | 높음 | ⭐⭐ |

---

## 💡 추천: Option A (`;` 사용)

```python
# sandbox.py Line 472, 291
# Before:
self.sandbox.shell.sendline(command + " && sleep 0.5")

# After:
self.sandbox.shell.sendline(command + " ; sleep 0.5")
```

**이유:**
1. **가장 간단** (1글자 변경)
2. **확실한 효과** (sleep 항상 실행)
3. **부작용 없음** (returncode는 첫 명령 기준)
4. **pexpect 안정화** (프롬프트 반환 보장)

**추가 고려:**
- returncode는 `echo $?`로 별도 확인
- `&&` vs `;`의 차이는 returncode 반환에만 영향
- 하지만 우리는 `echo $?`로 확인하므로 문제 없음!

---

## 🎯 다음 단계

1. `;` 로 변경
2. v2.6 재테스트
3. returncode 123 발생 여부 확인


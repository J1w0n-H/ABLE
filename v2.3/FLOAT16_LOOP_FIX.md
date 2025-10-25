# Float16 무한 루프 문제 및 해결

## 🔴 문제 발견: OSGeo/gdal

### **증상**
```
make -j4: 91번 실행
cmake:    151번 실행
```

**무한 루프 패턴**:
1. `make -j4` → Float16 링크 에러
2. error_parser: "Check library dependencies" (일반적 제안)
3. LLM: `cmake` 재실행 (잘못된 판단!)
4. LLM: `make -j4` 재실행
5. 같은 에러 → 1번으로 돌아감

### **에러 내용**
```
/usr/bin/ld: rasterio.cpp:(.text+0x41d90): undefined reference to `__extendhfsf2'
/usr/bin/ld: rasterio.cpp:(.text+0x41dae): more undefined references to `__extendhfsf2' follow
/usr/bin/ld: rasterio.cpp:(.text+0x41dbb): undefined reference to `__truncsfhf2'
/usr/bin/ld: rasterio.cpp:(.text+0x42db1): undefined reference to `__truncsfhf2'
/usr/bin/ld: rasterio.cpp:(.text+0x43701): undefined reference to `__truncdfhf2'
```

### **원인 분석**

**Float16 (half-precision floating point) 컴파일러 내장 함수 누락**:
- `__extendhfsf2`: half float → single float 변환
- `__truncsfhf2`: single float → half float 변환
- `__truncdfhf2`: double → half float 변환

이는 **컴파일러 런타임 라이브러리**(libgcc/compiler-rt) 문제입니다.

**기존 error_parser.py**:
- ✅ "undefined reference"는 감지
- ❌ Float16 특화 제안 없음
- ❌ LLM이 해결책을 찾지 못함 → cmake 재실행 반복

---

## ✅ 해결책 구현

### **error_parser.py 개선 (Line 181-186)**

**Before**:
```python
if 'undefined reference' in error_text:
    suggestions.add("Linker error: missing library. Check configure options or install -dev packages.")
    suggestions.add(f"Missing symbols detected. Check library dependencies.")
```

**After**:
```python
# 🆕 CRITICAL: Float16 (half-precision) link errors - MUST CHECK FIRST!
if '__extendhfsf2' in error_text or '__truncsfhf2' in error_text or '__truncdfhf2' in error_text:
    suggestions.add("🔴 Float16 (half-precision) link error detected!")
    suggestions.add("Solution: Disable Float16 in CMake → cd /repo/build && rm -rf * && cmake .. -DCMAKE_BUILD_TYPE=Release -DGDAL_USE_FLOAT16=OFF && make -j4")
    suggestions.add("Alternative 1: Install libgcc runtime: apt-get install libgcc-s1")
    suggestions.add("Alternative 2: Use GCC instead of Clang: export CC=gcc CXX=g++ && cd /repo/build && rm -rf * && cmake .. && make -j4")
elif 'undefined reference' in error_text:
    suggestions.add("Linker error: missing library. Check configure options or install -dev packages.")
    suggestions.add(f"Missing symbols detected. Check library dependencies.")
```

---

## 🎯 효과

### **다음 실행 시 LLM이 받을 메시지**:

```
🚨 CRITICAL ERRORS DETECTED:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. undefined reference to `__extendhfsf2'
2. undefined reference to `__truncsfhf2'
3. undefined reference to `__truncdfhf2'
...

💡 SUGGESTED FIXES:
   • 🔴 Float16 (half-precision) link error detected!
   • Solution: Disable Float16 in CMake → cd /repo/build && rm -rf * && cmake .. -DCMAKE_BUILD_TYPE=Release -DGDAL_USE_FLOAT16=OFF && make -j4
   • Alternative 1: Install libgcc runtime: apt-get install libgcc-s1
   • Alternative 2: Use GCC instead of Clang: export CC=gcc CXX=g++ && cd /repo/build && rm -rf * && cmake .. && make -j4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### **예상 LLM 행동**:
1. ✅ Float16 에러 인식
2. ✅ CMake에 `-DGDAL_USE_FLOAT16=OFF` 추가
3. ✅ 빌드 재시도
4. ✅ 성공 (Float16 비활성화 상태)

---

## 📊 현재 상태

### **OSGeo/gdal**:
- 상태: **무한 루프 중** (cmake/make 반복)
- 턴: 33/100 남음
- 권장 조치: **프로세스 종료 후 재시작** (새 error_parser 적용)

### **개선된 error_parser.py**:
- ✅ Float16 에러 감지 추가
- ✅ 구체적인 해결책 제시
- ✅ 다음 실행부터 자동 적용

---

## 🔧 수동 해결 (필요시)

GDAL 컨테이너에 직접 접속해서 수정:

```bash
# Docker 컨테이너 찾기
docker ps | grep gdal

# 컨테이너 접속
docker exec -it <container_id> bash

# Float16 비활성화 후 재빌드
cd /repo/build
rm -rf *
cmake .. -DCMAKE_BUILD_TYPE=Release -DGDAL_USE_FLOAT16=OFF
make -j4
```

---

## 📝 결론

- **문제**: Float16 링크 에러를 error_parser가 감지하지 못해 무한 루프
- **해결**: 특화된 에러 감지 및 해결책 제안 추가
- **효과**: 다음 실행부터 자동으로 Float16 비활성화하여 빌드 성공 예상
- **현재**: GDAL은 무한 루프 중이므로 재시작 권장

---

**다음 배치 실행 시 이 문제는 자동으로 해결될 것입니다!** 🎯


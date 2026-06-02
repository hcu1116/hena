# =============================================================
# Python 기초 — C 개발자를 위한 비교 학습
# =============================================================
# 실행 방법: python hello.py
# =============================================================


# ── 1. 변수와 자료형 ──────────────────────────────────────────
# C:      int x = 10;   → 타입을 먼저 선언하고 값을 넣음
# Python: x = 10        → 타입 선언 없음. 값이 들어가면 타입이 자동으로 정해짐
#         이걸 "동적 타이핑"이라고 함

name = "황찬웅"       # C: char name[] = "황찬웅";
age = 22              # C: int age = 22;
height = 175.5        # C: float height = 175.5;
is_student = True     # C: bool is_student = true;  ← Python은 True/False 대문자

# type()으로 타입 확인 (C엔 없는 기능 — 런타임에 타입을 물어볼 수 있음)
print("=== 1. 변수와 자료형 ===")
print(type(name))         # <class 'str'>
print(type(age))          # <class 'int'>
print(type(is_student))   # <class 'bool'>


# ── 2. f-string ───────────────────────────────────────────────
# C:      printf("이름: %s, 나이: %d\n", name, age);
# Python: 문자열 앞에 f를 붙이면, {} 안에 변수를 바로 넣을 수 있음
#         %d, %s 같은 포맷 기호 외울 필요 없음

print("\n=== 2. f-string ===")
print(f"이름: {name}, 나이: {age}세")
print(f"키: {height}cm")
print(f"계산도 가능: {age * 365}일 살았음")   # {} 안에 식도 쓸 수 있음


# ── 3. 리스트 (List) ──────────────────────────────────────────
# C:    int scores[3] = {90, 85, 78};   → 크기 고정, 같은 타입만
# Python: 크기 자동 조절, 타입도 섞어도 됨 (C의 동적 배열보다 훨씬 편함)

print("\n=== 3. 리스트 ===")
scores = [90, 85, 78]

print(scores[0])    # C와 똑같이 0부터 시작
print(scores[-1])   # 음수 인덱스: 뒤에서 접근. -1이 마지막 (C엔 없는 편의 기능)

scores.append(95)           # 끝에 추가 (C: realloc 없이 그냥 붙임)
print(f"추가 후: {scores}")
print(f"길이: {len(scores)}")   # C: sizeof(arr)/sizeof(arr[0]) 대신 len()


# ── 4. 딕셔너리 (Dictionary) ──────────────────────────────────
# C:    struct Person { char* name; int age; };  → 미리 구조 정의 필요
# Python: 키-값 쌍을 즉석에서 만들 수 있음. 키는 문자열, 값은 뭐든 됨

print("\n=== 4. 딕셔너리 ===")
person = {
    "name": "황찬웅",
    "age": 22,
    "major": "인공지능",
}

print(person["name"])        # 키로 접근 (C 구조체의 person.name 같은 느낌)
person["grade"] = 3          # 새 키-값 추가 (C 구조체는 나중에 필드 추가 불가)
print(f"전공: {person['major']}, 학년: {person['grade']}")


# ── 5. 조건문 ─────────────────────────────────────────────────
# C:    if (age >= 20) { ... } else if (...) { ... } else { ... }
# Python: 중괄호({}) 없음. 대신 콜론(:) + 들여쓰기(4칸)로 블록을 나눔
#         else if → elif 로 줄임

print("\n=== 5. 조건문 ===")
if age >= 20:
    print("성인입니다")       # 이 들여쓰기가 C의 {} 역할
elif age >= 14:               # C의 else if
    print("청소년입니다")
else:
    print("어린이입니다")

# 한 줄 조건: Python만의 표현 (C의 삼항연산자 ? : 와 비슷)
label = "학생" if is_student else "비학생"
print(f"신분: {label}")


# ── 6. 반복문 ─────────────────────────────────────────────────
# C:    for (int i = 0; i < 3; i++) { ... }
# Python의 for는 "무언가를 순서대로 꺼내는" 방식

print("\n=== 6. 반복문 ===")

# range(n): 0부터 n-1까지의 숫자를 생성 → C의 for(i=0; i<n; i++)
for i in range(3):
    print(f"  range: {i}")

# 리스트를 직접 순회 — C엔 없는 방식. 인덱스 없이 값을 바로 꺼냄
for score in scores:
    print(f"  점수: {score}")

# enumerate: 인덱스와 값을 동시에 꺼냄 → C의 for(i=0; ...) arr[i]와 같은 역할
for i, score in enumerate(scores):
    print(f"  [{i}] {score}점")

# while은 C와 거의 동일 (중괄호 대신 들여쓰기만 다름)
count = 0
while count < 2:
    print(f"  while: {count}")
    count += 1    # C: count++; 도 되지만 Python은 ++ 연산자 없음


print("\n✅ 완료! C와 Python 기초 비교 끝.")

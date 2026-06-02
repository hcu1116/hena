# =============================================================
# Python 클래스(OOP) — C struct와 비교 학습
# 주제: 환자(Patient) 클래스
# =============================================================
# C의 struct:  데이터만 묶음. 함수는 밖에 따로 만들어야 함.
# Python 클래스: 데이터(속성) + 함수(메서드)를 하나로 묶음.
# =============================================================

# C라면 이렇게 했을 것:
#
#   typedef struct {
#       char name[50];
#       int  age;
#       int  heart_rate;
#   } Patient;
#
#   bool is_tachycardia(Patient* p) { return p->heart_rate > 100; }
#   void introduce(Patient* p)      { printf(...); }
#
# Python은 데이터와 그 데이터를 다루는 함수를 class 안에 같이 씀


class Patient:   # class 키워드로 새 타입을 정의 (C의 typedef struct와 같은 역할)

    # ── __init__: 생성자 ────────────────────────────────────────
    # C:      Patient p = {"이름", 25, 72};  혹은 별도 init 함수
    # Python: 객체를 만들 때 자동으로 호출되는 특별 메서드
    #
    # self가 뭔가?
    #   C의 포인터 p->name 에서 p* 에 해당하는 것.
    #   "지금 이 객체 자신"을 가리키는 변수.
    #   Python에서는 모든 메서드의 첫 번째 인자로 self를 써야 함 (관례적 이름).

    def __init__(self, name, age, heart_rate):
        # self.name = name  →  이 객체의 name 속성에 값을 저장
        # C:  p->name = name;  과 완전히 같은 의미
        self.name = name
        self.age = age
        self.heart_rate = heart_rate   # 단위: BPM (beats per minute)

    # ── 메서드 1: is_tachycardia ────────────────────────────────
    # 심박수가 100 BPM을 넘으면 빈맥(tachycardia) → True 반환
    #
    # C:      bool is_tachycardia(Patient* p) { return p->heart_rate > 100; }
    # Python: 클래스 안에 def로 정의. 첫 인자는 항상 self.
    #         호출할 때는 patient.is_tachycardia() — self는 자동으로 넘어감

    def is_tachycardia(self):
        return self.heart_rate > 100   # True 또는 False 반환

    # ── 메서드 2: introduce ─────────────────────────────────────
    # 환자 정보를 출력하는 메서드
    # C라면 void introduce(Patient* p) { printf(...); } 를 밖에 따로 만들었을 것

    def introduce(self):
        # 빈맥 여부를 한 줄 조건식으로 판단 (지난 시간에 배운 if-else 한 줄 버전)
        status = "⚠️  빈맥 의심" if self.is_tachycardia() else "정상 범위"

        # self.name 처럼 자신의 속성에 자유롭게 접근 가능
        print(f"환자: {self.name} ({self.age}세)")
        print(f"  심박수: {self.heart_rate} BPM  →  {status}")


# =============================================================
# 객체 생성 및 메서드 호출
# =============================================================
# C:      Patient p1 = {"김민준", 35, 72};
# Python: 클래스 이름을 함수처럼 호출하면 객체(instance)가 만들어짐.
#         이때 __init__이 자동 실행됨.

print("=== 환자 객체 생성 ===\n")

p1 = Patient("김민준", 35, 72)    # 정상 심박수
p2 = Patient("이서연", 28, 115)   # 빈맥 (100 초과)
p3 = Patient("박준혁", 51, 98)    # 경계선 근처

# ── 메서드 호출 ─────────────────────────────────────────────
# C:      introduce(&p1);         ← 포인터를 직접 넘겨야 함
# Python: p1.introduce()          ← 점(.) 뒤에 메서드 이름. self는 자동.

p1.introduce()
print()
p2.introduce()
print()
p3.introduce()

# ── 속성에 직접 접근 ────────────────────────────────────────
# C:      p1.heart_rate = 80;     ← 구조체 필드 직접 수정
# Python: 동일하게 점(.)으로 접근하고 수정 가능

print("\n=== 심박수 업데이트 후 재확인 ===\n")
p3.heart_rate = 104    # p3의 심박수를 갱신
p3.introduce()         # 같은 메서드인데 결과가 달라짐 (상태가 바뀌었으니까)

# ── is_tachycardia 단독 호출 ───────────────────────────────
print("\n=== is_tachycardia 반환값 확인 ===\n")
for patient in [p1, p2, p3]:
    result = patient.is_tachycardia()   # True / False 반환
    print(f"  {patient.name}: {result}")

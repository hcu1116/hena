# =============================================================
# numpy & pandas 기초 — 심박수 데이터로 배우기
# =============================================================
# numpy:  C의 배열을 강력하게 확장한 것. 수학 연산에 최적화.
# pandas: 표(DataFrame)로 데이터를 다루는 도구. 엑셀을 코드로 하는 느낌.
# =============================================================

import numpy as np    # 관례적으로 np로 줄여서 씀
import pandas as pd   # 관례적으로 pd로 줄여서 씀


# =============================================================
# 1. numpy 기초 — 심박수 배열
# =============================================================
# C:   int hr[10] = {72, 75, 68, ...};  → 고정 크기, 수동 계산
# numpy: 배열 선언 한 줄, 평균/최대/표준편차 함수로 즉시 계산

print("=" * 45)
print("1. numpy — 심박수 배열 연산")
print("=" * 45)

# np.array(): Python 리스트를 numpy 배열로 만듦
# 겉모습은 리스트와 비슷하지만, 수학 연산이 훨씬 빠르고 편함
hr_data = np.array([72, 75, 68, 110, 95, 82, 115, 70, 88, 103])

print(f"심박수 데이터: {hr_data}")
print(f"타입: {type(hr_data)}")   # <class 'numpy.ndarray'>

# C라면 평균을 구하기 위해 for 루프를 직접 짜야 함:
#   int sum = 0;
#   for (int i = 0; i < 10; i++) sum += hr_data[i];
#   float mean = (float)sum / 10;
#
# numpy는 함수 하나로 끝남:
print(f"\n평균(mean):     {np.mean(hr_data):.1f} BPM")
print(f"최대(max):      {np.max(hr_data)} BPM")
print(f"최소(min):      {np.min(hr_data)} BPM")

# 표준편차: 데이터가 평균에서 얼마나 퍼져 있는지 (HRV 분석의 핵심 지표)
# 클수록 심박이 불규칙하다는 의미 — 기면증 환자의 특징
print(f"표준편차(std):  {np.std(hr_data):.1f} BPM  ← 클수록 불규칙")

# 불리언 마스킹: 조건을 배열 전체에 한 번에 적용
# C:  for 루프 + if 문 조합으로 직접 골라내야 함
# numpy: 조건식 하나로 True/False 배열을 만들고, 그걸로 필터
over_100 = hr_data[hr_data > 100]   # 100 초과인 값만 골라냄
print(f"\n100 BPM 초과 에피소드: {over_100}")
print(f"발생 횟수: {len(over_100)}회")


# =============================================================
# 2. pandas 기초 — 시계열 심박수 표(DataFrame)
# =============================================================
# DataFrame = 행(row) + 열(column)로 구성된 표.
# C의 구조체 배열과 비슷하지만, 열 이름으로 접근하고 분석 함수가 내장됨.

print("\n" + "=" * 45)
print("2. pandas — 심박수 DataFrame")
print("=" * 45)

# 딕셔너리로 데이터를 정의하고 pd.DataFrame()에 넘기면 표가 만들어짐
# 각 키(key)가 열 이름, 값(value) 리스트가 그 열의 데이터
data = {
    "time":       ["06:00", "08:00", "10:00", "12:00", "14:00",
                   "16:00", "18:00", "20:00", "22:00", "00:00"],
    "heart_rate": [72,      110,     75,       88,     115,
                   82,      95,      68,       103,    70],
    "movement":   [0.1,     0.8,     0.3,      0.9,    0.2,
                   0.7,     0.5,     0.1,      0.1,    0.0],
    # movement: 0.0(정지) ~ 1.0(활발한 움직임) — 가속도계 데이터 가정
}

df = pd.DataFrame(data)

# DataFrame을 print하면 표 형태로 예쁘게 출력됨
print(df)
print(f"\n행 수: {len(df)},  열 수: {len(df.columns)}")


# =============================================================
# 3. 열 단위 연산
# =============================================================
# df["열이름"] 으로 열 하나를 꺼냄 → numpy 배열처럼 연산 가능

print("\n" + "=" * 45)
print("3. heart_rate 열 분석")
print("=" * 45)

hr_col = df["heart_rate"]   # 심박수 열만 꺼냄

# .mean(), .max() 등은 pandas가 자체 제공하는 메서드
print(f"평균 심박수: {hr_col.mean():.1f} BPM")
print(f"최대 심박수: {hr_col.max()} BPM")
print(f"최소 심박수: {hr_col.min()} BPM")

# describe(): 한 번에 통계 요약을 뽑아줌 (탐색적 분석 시작점으로 자주 씀)
print(f"\n통계 요약:\n{hr_col.describe().round(1)}")


# =============================================================
# 4. 필터링 — 심박수 100 초과 행만 보기
# =============================================================
# C:   for 루프 + if 조건으로 한 행씩 검사
# pandas: 조건식 하나로 해당 행 전체를 즉시 추출

print("\n" + "=" * 45)
print("4. 빈맥 의심 구간 필터링 (HR > 100)")
print("=" * 45)

# df["heart_rate"] > 100 은 True/False로 이루어진 열을 만들고,
# 그걸 df[ ] 안에 넣으면 True인 행만 추출됨
tachycardia = df[df["heart_rate"] > 100]

print(tachycardia)
print(f"\n총 {len(tachycardia)}개 구간에서 빈맥 의심")

# reset_index: 필터 후 인덱스 번호가 원래대로 남아 있는데, 0부터 다시 매김
tachycardia_clean = tachycardia.reset_index(drop=True)
print(f"\n(인덱스 재정렬 후)\n{tachycardia_clean}")

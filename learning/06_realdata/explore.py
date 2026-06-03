import pandas as pd

# ── 1. 파일 읽기 ──────────────────────────────────────────────
# 어제 가짜 데이터: pd.DataFrame({"hr": [60, 75, ...]})  직접 만들었음
# 진짜 데이터: 파일에서 읽어야 함. 형식이 "타임스탬프,BPM" 이므로
#   - header=None  : 첫 줄이 컬럼명이 아님 (그냥 데이터)
#   - names=[...]  : 컬럼명을 내가 직접 붙여줌
df = pd.read_csv(
    "data/4314139_heartrate.txt",
    header=None,
    names=["timestamp", "bpm"],
)

# ── 2. 기본 정보 ──────────────────────────────────────────────
print("=" * 50)
print(f"총 줄 수: {len(df)}행")
print()
print("[ 첫 5줄 ]")
print(df.head())
print()
print("[ 마지막 5줄 ]")
print(df.tail())
print()

# dtypes: 각 컬럼이 어떤 타입으로 읽혔는지
# 어제 가짜 데이터는 타입을 신경 안 썼지만,
# 진짜 데이터는 타입이 맞지 않으면 계산이 틀릴 수 있음
print("[ 컬럼 타입 ]")
print(df.dtypes)
print()

# ── 3. 기본 통계 ──────────────────────────────────────────────
print("=" * 50)
print("[ 심박수(bpm) 기본 통계 ]")
print(f"  평균:   {df['bpm'].mean():.1f} BPM")
print(f"  최소:   {df['bpm'].min()} BPM")
print(f"  최대:   {df['bpm'].max()} BPM")
print(f"  표준편차: {df['bpm'].std():.1f} BPM")
print()

# describe()는 위 통계를 한 번에 보여주는 편의 함수
print("[ describe() — 한 눈에 보기 ]")
print(df["bpm"].describe())
print()

# ── 4. 이상한 값 확인 ─────────────────────────────────────────
print("=" * 50)
print("[ 이상값 점검 ]")

# 4-1. 결측치 (NaN): 데이터가 아예 없는 칸
missing = df.isnull().sum()
print(f"  결측치: timestamp={missing['timestamp']}개, bpm={missing['bpm']}개")

# 4-2. 말도 안 되는 심박수 (의학적으로 30 미만 or 220 초과는 의심)
weird = df[(df["bpm"] < 30) | (df["bpm"] > 220)]
print(f"  비정상 BPM(<30 or >220): {len(weird)}개")
if len(weird) > 0:
    print(weird)

# 4-3. 측정 간격 확인 — timestamp 차이를 계산
# diff()는 바로 앞 행과의 차이를 구함
intervals = df["timestamp"].diff()
print()
print("[ 측정 간격(초) 통계 ]")
print(f"  평균 간격: {intervals.mean():.1f}초")
print(f"  최소 간격: {intervals.min():.1f}초")
print(f"  최대 간격: {intervals.max():.1f}초")
print()
print("  → 어제 가짜 데이터는 간격이 일정했지만,")
print("    Apple Watch는 배터리/움직임에 따라 간격이 들쑥날쑥함.")
print("    이게 진짜 웨어러블 데이터의 현실.")

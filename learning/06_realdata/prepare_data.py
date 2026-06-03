import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════
# 왜 데이터 준비가 필요한가?
#
# 심박수: 불규칙 간격, 10,936행
# 가속도: ~24Hz 고빈도, 691,859행
# 수면 라벨: 정확히 30초 간격, 970행
#
# ML 모델에 넣으려면 한 행 = 30초 구간, 열 = 피처 형태여야 함.
# 세 파일의 시간 축을 30초 단위로 통일하는 게 이 파일의 전부.
# ══════════════════════════════════════════════════════════════

# ── 1. 파일 읽기 ──────────────────────────────────────────────
hr = pd.read_csv(
    "data/4314139_heartrate.txt",
    header=None, names=["ts", "bpm"],
)
sleep = pd.read_csv(
    "data/4314139_labeled_sleep.txt",
    header=None, names=["ts", "stage"], sep=" ",
)
accel = pd.read_csv(
    "data/4314139_acceleration.txt",
    header=None, names=["ts", "x", "y", "z"], sep=" ",
)

print(f"읽기 완료 — HR: {len(hr)}행 / Sleep: {len(sleep)}행 / Accel: {len(accel)}행")

# ── 2. 수면 기록 구간만 자르기 ────────────────────────────────
# 수면 라벨은 ts=0부터 시작. 그 이전(-1430초, -571072초 등)은
# 낮에 애플워치 차고 있던 기록이므로 수면 분석에 불필요.
hr    = hr[hr["ts"] >= 0].copy()
accel = accel[accel["ts"] >= 0].copy()

print(f"수면 구간 필터 후 — HR: {len(hr)}행 / Accel: {len(accel)}행")

# ── 3. "30초 창" 배정: 핵심 시간 정렬 ────────────────────────
#
# 수면 라벨은 30초 단위로 기록됨 (PSG 표준: 30초 = 1 에포크).
# 즉 ts=0은 0~30초 구간, ts=30은 30~60초 구간을 뜻함.
#
# HR 타임스탬프 ts=47.3 → 이 측정은 30~60초 구간에 속함 → window=30
# HR 타임스탬프 ts=91.0 → 이 측정은 90~120초 구간에 속함 → window=90
#
# 공식: window = (ts를 30으로 나눈 몫) × 30
#        = floor(ts / 30) * 30
#
# C로 표현하면: window = (int)(ts / 30) * 30
hr["window"]    = (hr["ts"] // 30) * 30
accel["window"] = (accel["ts"] // 30) * 30

# ── 4. 가속도 크기(magnitude) 계산 ───────────────────────────
# x, y, z 세 방향 가속도를 하나의 "움직임 강도" 숫자로 합침.
# 피타고라스 정리의 3D 버전: sqrt(x²+y²+z²)
# 방향 상관없이 "얼마나 많이 움직였는가"만 남김.
accel["mag"] = np.sqrt(accel["x"]**2 + accel["y"]**2 + accel["z"]**2)

# ── 5. 30초 창별 통계 집계 ───────────────────────────────────
# groupby("window"): 같은 window 값끼리 묶기
# agg(["mean","std"]): 그 묶음 안에서 평균과 표준편차 계산
#
# 표준편차(std)를 피처로 쓰는 이유:
#   평균이 같아도 "안정적 60bpm"과 "60~90을 왔다갔다"는 다른 상태.
#   std가 크면 불규칙 = 각성/REM 가능성이 높음.

hr_feat = (
    hr.groupby("window")["bpm"]
    .agg(hr_mean="mean", hr_std="std")
    .reset_index()
    .rename(columns={"window": "ts"})
)

accel_feat = (
    accel.groupby("window")["mag"]
    .agg(accel_mean="mean", accel_std="std")
    .reset_index()
    .rename(columns={"window": "ts"})
)

print(f"\n30초 창 집계 후 — HR 창: {len(hr_feat)}개 / Accel 창: {len(accel_feat)}개")

# ── 6. 세 데이터 합치기 ───────────────────────────────────────
# sleep 라벨을 기준(left)으로, HR과 가속도 피처를 ts 기준 병합.
# how="left": 수면 라벨에 있는 창만 남김. 피처가 없는 창은 NaN.
df = sleep.merge(hr_feat, on="ts", how="left")
df = df.merge(accel_feat, on="ts", how="left")

print(f"\n병합 결과: {len(df)}행 × {len(df.columns)}열")
print(df.head(10).to_string(index=False))

# ── 7. 결측치 확인 ────────────────────────────────────────────
# 어떤 30초 창에 HR 측정이 하나도 없으면 hr_mean/hr_std = NaN.
# 이런 창은 ML에 넣을 수가 없어서 확인 필요.
missing = df.isnull().sum()
print(f"\n결측치 현황:\n{missing}")

# -1 라벨(수면 전/후)은 예측 대상이 아니므로 제거
df_clean = df[df["stage"] != -1].copy()
# 그 다음 NaN 행 제거
df_clean = df_clean.dropna()

print(f"\n정리 후 (stage=-1 제거 + NaN 제거): {len(df_clean)}행")
print(f"수면 단계 분포:\n{df_clean['stage'].value_counts().sort_index()}")

# ── 8. CSV 저장 ───────────────────────────────────────────────
# index=False: 행 번호(0,1,2...) 는 열로 저장 안 함
output_path = "prepared.csv"
df_clean.to_csv(output_path, index=False)
print(f"\n저장 완료: {output_path}")
print(f"최종 데이터 형태: {df_clean.shape[0]}행 × {df_clean.shape[1]}열")
print(f"열 목록: {list(df_clean.columns)}")
print("\n[ 첫 5행 미리보기 ]")
print(df_clean.head().to_string(index=False))

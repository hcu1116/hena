import pandas as pd
import numpy as np
import os

# ══════════════════════════════════════════════════════════════
# prepare_multi.py 에서 HRV 피처 3개 추가한 버전
#
# 기존 피처 4개:  hr_mean, hr_std, accel_mean, accel_std
# 추가 피처 3개:  hrv_rmssd, hrv_sdnn, hrv_pnn50
#
# HRV 계산 원리:
#   BPM(박/분) → RR interval(ms) = 60000 / BPM
#   RR interval = 심장이 한 번 뛰는 데 걸리는 시간(밀리초)
#
#   RMSSD = √( mean( (RR[i+1] - RR[i])² ) )
#     → 연속 RR 차이의 RMS. 빠른 변동 = 부교감신경 세기.
#     → N3(서파수면)·REM에서 높음, 각성에서 낮음.
#
#   SDNN = std(RR)
#     → 전체 RR 변동성. 자율신경 전체 균형.
#     → N3에서 가장 높음 (안정적 부교감 우위).
#
#   pNN50 = |ΔRR| > 50ms 비율 (%)
#     → RMSSD의 역치 버전. 50ms는 임상 표준 기준.
#     → N3에서 높음.
#
# 데이터 현실:
#   30초 창에 ~6개 샘플(5초 간격). 임상 ECG보다 적지만
#   웨어러블 HRV 연구에서 표준적으로 쓰는 근사 방법.
# ══════════════════════════════════════════════════════════════

DATA_DIR = "data"

SUBJECTS = [
    "4314139",
    "2598705",
    "5498603",
    "1066528",
    "1455390",
    "2638030",
    "3509524",
]


def compute_hrv(bpm_series: pd.Series) -> tuple[float, float, float]:
    """BPM 시리즈 → (rmssd, sdnn, pnn50) 반환.

    샘플이 2개 미만이면 NaN 반환 (창이 너무 짧아 계산 불가).
    """
    if len(bpm_series) < 2:
        return np.nan, np.nan, np.nan

    # BPM → RR interval (밀리초)
    rr = 60000.0 / bpm_series.values

    # SDNN: RR 전체 표준편차 (ddof=1: 표본 표준편차)
    sdnn = np.std(rr, ddof=1) if len(rr) > 1 else np.nan

    # RMSSD: 연속 RR 차이의 제곱평균제곱근
    diff = np.diff(rr)           # 길이 n-1
    rmssd = np.sqrt(np.mean(diff ** 2))

    # pNN50: 차이가 50ms 초과인 비율 (0~100%)
    pnn50 = np.mean(np.abs(diff) > 50) * 100

    return rmssd, sdnn, pnn50


def hrv_agg(bpm_series: pd.Series) -> pd.Series:
    """groupby().apply()에 쓸 수 있도록 Series로 감싼 래퍼."""
    rmssd, sdnn, pnn50 = compute_hrv(bpm_series)
    return pd.Series({
        "hrv_rmssd": rmssd,
        "hrv_sdnn":  sdnn,
        "hrv_pnn50": pnn50,
    })


def process_one_subject(subject_id: str) -> pd.DataFrame | None:
    """한 사람의 데이터를 30초 창 피처(기존 4 + HRV 3)로 변환해 반환."""
    hr_path    = os.path.join(DATA_DIR, f"{subject_id}_heartrate.txt")
    accel_path = os.path.join(DATA_DIR, f"{subject_id}_acceleration.txt")
    sleep_path = os.path.join(DATA_DIR, f"{subject_id}_labeled_sleep.txt")

    for p in [hr_path, accel_path, sleep_path]:
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            print(f"  [skip] {p} 없음 또는 비어 있음")
            return None

    # ── 읽기 ─────────────────────────────────────────────────
    hr    = pd.read_csv(hr_path,    header=None, names=["ts", "bpm"])
    sleep = pd.read_csv(sleep_path, header=None, names=["ts", "stage"], sep=" ")
    accel = pd.read_csv(accel_path, header=None, names=["ts", "x", "y", "z"], sep=" ")

    # 수면 구간(ts >= 0)만
    hr    = hr[hr["ts"] >= 0].copy()
    accel = accel[accel["ts"] >= 0].copy()

    # 30초 창 번호 배정
    hr["window"]    = (hr["ts"] // 30) * 30
    accel["window"] = (accel["ts"] // 30) * 30

    accel["mag"] = np.sqrt(accel["x"]**2 + accel["y"]**2 + accel["z"]**2)

    # ── 기존 피처: hr_mean, hr_std ────────────────────────────
    hr_basic = (
        hr.groupby("window")["bpm"]
        .agg(hr_mean="mean", hr_std="std")
        .reset_index()
        .rename(columns={"window": "ts"})
    )

    # ── HRV 피처: rmssd, sdnn, pnn50 ─────────────────────────
    # apply()가 Series를 반환하면 multi-index Series가 되므로
    # unstack()으로 columns가 있는 DataFrame으로 펼쳐야 함
    hr_hrv = (
        hr.groupby("window")["bpm"]
        .apply(hrv_agg)
        .unstack()              # (window × metric) DataFrame으로 변환
        .reset_index()
        .rename(columns={"window": "ts"})
    )

    # ── 가속도 피처 ───────────────────────────────────────────
    accel_feat = (
        accel.groupby("window")["mag"]
        .agg(accel_mean="mean", accel_std="std")
        .reset_index()
        .rename(columns={"window": "ts"})
    )

    # ── 병합 ─────────────────────────────────────────────────
    df = sleep.merge(hr_basic,   on="ts", how="left")
    df = df.merge(hr_hrv,        on="ts", how="left")
    df = df.merge(accel_feat,    on="ts", how="left")

    # 정리
    df = df[df["stage"] != -1].copy()
    df = df.dropna()

    if len(df) == 0:
        print(f"  [skip] {subject_id} — 유효 데이터 없음")
        return None

    df["subject_id"] = subject_id

    print(f"  ✓ {subject_id}: {len(df)}개 창  "
          f"(RMSSD 평균: {df['hrv_rmssd'].mean():.1f}ms, "
          f"SDNN: {df['hrv_sdnn'].mean():.1f}ms)")
    return df


# ── 메인 ─────────────────────────────────────────────────────
all_dfs = []

print("=" * 60)
print("[ HRV 피처 포함 전처리 시작 ]")
print("=" * 60)

for sid in SUBJECTS:
    print(f"\n▶ {sid} 처리 중...")
    result = process_one_subject(sid)
    if result is not None:
        all_dfs.append(result)

print("\n" + "=" * 60)

if not all_dfs:
    print("처리된 데이터가 없습니다.")
    exit(1)

combined = pd.concat(all_dfs, ignore_index=True)

print(f"\n[ 합치기 완료 ]")
print(f"  총 {len(combined)}개 창, {combined['subject_id'].nunique()}명")
print(f"  열 목록: {list(combined.columns)}")

# HRV 지표 분포 확인 — 수면 단계별로 다른지 보기
print("\n[ 수면 단계별 HRV 평균 — 의학 이론과 맞는지 확인 ]")
print("  (N3에서 RMSSD·pNN50이 가장 높아야 함)")
STAGE_NAME = {0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}
stage_hrv = combined.groupby("stage")[["hrv_rmssd", "hrv_sdnn", "hrv_pnn50"]].mean()
for stage, row in stage_hrv.iterrows():
    name = STAGE_NAME.get(stage, f"stage{stage}")
    print(f"  {name:12s}  RMSSD={row['hrv_rmssd']:6.1f}ms  "
          f"SDNN={row['hrv_sdnn']:6.1f}ms  pNN50={row['hrv_pnn50']:5.1f}%")

# 저장
output_path = "prepared_multi_hrv.csv"
combined.to_csv(output_path, index=False)
print(f"\n저장 완료: {output_path}")
print(f"최종 형태: {combined.shape[0]}행 × {combined.shape[1]}열")
print("\n[ 첫 3행 미리보기 ]")
print(combined.head(3).to_string(index=False))

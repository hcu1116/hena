import pandas as pd
import numpy as np
import os

# ══════════════════════════════════════════════════════════════
# 여러 사람 데이터를 하나로 합치는 이유
#
# 지난번(prepare_data.py)은 한 사람(4314139)만 처리했음.
# → 모델이 "이 사람 패턴"만 학습 → 다른 사람엔 안 맞을 수 있음.
#
# 이번엔 7명을 합치고 'subject_id' 열을 붙임.
# 이 열이 나중에 "사람 단위 train/test 분리"의 열쇠가 됨.
# ══════════════════════════════════════════════════════════════

DATA_DIR = "data"

SUBJECTS = [
    "4314139",   # 이미 있는 데이터
    "2598705",
    "5498603",
    "1066528",
    "1455390",
    "2638030",
    "3509524",
]


def process_one_subject(subject_id: str) -> pd.DataFrame | None:
    """한 사람의 세 파일을 읽어 30초 창 피처로 변환하고 반환."""
    hr_path    = os.path.join(DATA_DIR, f"{subject_id}_heartrate.txt")
    accel_path = os.path.join(DATA_DIR, f"{subject_id}_acceleration.txt")
    sleep_path = os.path.join(DATA_DIR, f"{subject_id}_labeled_sleep.txt")

    # 파일 존재 확인: 없으면 건너뜀
    for p in [hr_path, accel_path, sleep_path]:
        if not os.path.exists(p) or os.path.getsize(p) == 0:
            print(f"  [skip] {p} 없음 또는 비어 있음")
            return None

    # ── 1. 읽기 ──────────────────────────────────────────────
    hr    = pd.read_csv(hr_path,    header=None, names=["ts", "bpm"])
    sleep = pd.read_csv(sleep_path, header=None, names=["ts", "stage"], sep=" ")
    accel = pd.read_csv(accel_path, header=None, names=["ts", "x", "y", "z"], sep=" ")

    # ── 2. 수면 구간만 자르기 ─────────────────────────────────
    # ts < 0 은 수면 시작 전 낮 활동 기록 → 제외
    hr    = hr[hr["ts"] >= 0].copy()
    accel = accel[accel["ts"] >= 0].copy()

    # ── 3. 30초 창 배정 ──────────────────────────────────────
    # 수면 PSG 표준: 1 에포크 = 30초
    # ts=47.3 → 30~60초 구간 → window=30
    # floor(47.3 / 30) * 30 = 1 * 30 = 30
    hr["window"]    = (hr["ts"] // 30) * 30
    accel["window"] = (accel["ts"] // 30) * 30

    # ── 4. 가속도 크기 (3D 피타고라스) ───────────────────────
    accel["mag"] = np.sqrt(accel["x"]**2 + accel["y"]**2 + accel["z"]**2)

    # ── 5. 30초 창별 통계 집계 ───────────────────────────────
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

    # ── 6. 병합 ──────────────────────────────────────────────
    df = sleep.merge(hr_feat, on="ts", how="left")
    df = df.merge(accel_feat, on="ts", how="left")

    # ── 7. 정리 ──────────────────────────────────────────────
    # stage=-1: 수면 전/후 기록 (예측 대상 아님)
    df = df[df["stage"] != -1].copy()
    df = df.dropna()

    if len(df) == 0:
        print(f"  [skip] {subject_id} — 유효 데이터 없음")
        return None

    # ── 8. subject_id 열 추가 ─────────────────────────────────
    # 이 열이 핵심:
    #   나중에 "subject_id가 3509524인 행은 test"처럼 사람 단위로
    #   train/test를 나눌 수 있게 됨.
    #   랜덤 분리였다면 이 정보가 필요 없지만, 진짜 일반화 평가엔 필수.
    df["subject_id"] = subject_id

    print(f"  ✓ {subject_id}: {len(df)}개 창, "
          f"stage 분포: {df['stage'].value_counts().to_dict()}")
    return df


# ── 메인: 전체 처리 ───────────────────────────────────────────
all_dfs = []

print("=" * 55)
print("[ 전체 피험자 처리 시작 ]")
print("=" * 55)

for sid in SUBJECTS:
    print(f"\n▶ {sid} 처리 중...")
    result = process_one_subject(sid)
    if result is not None:
        all_dfs.append(result)

print("\n" + "=" * 55)

if len(all_dfs) == 0:
    print("처리된 데이터가 없습니다. 파일을 확인하세요.")
    exit(1)

# 7명 데이터를 세로로 쌓기
# ignore_index=True: 각 사람별 행 번호가 겹치므로 새로 매김 (0, 1, 2, ...)
combined = pd.concat(all_dfs, ignore_index=True)

print(f"\n[ 합치기 완료 ]")
print(f"  총 {len(combined)}개 창")
print(f"  피험자 수: {combined['subject_id'].nunique()}명")
print(f"  열 목록: {list(combined.columns)}")

print(f"\n[ 피험자별 창 개수 ]")
print(combined.groupby("subject_id").size().rename("창 수").to_string())

print(f"\n[ 전체 수면 단계 분포 ]")
STAGE_NAME = {-1: "Pre/Post", 0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}
stage_dist = combined["stage"].value_counts().sort_index()
for stage, count in stage_dist.items():
    name = STAGE_NAME.get(stage, f"stage{stage}")
    bar = "█" * int(count / 10)
    print(f"  {name:12s} {count:5d}  {bar}")

# 저장
output_path = "prepared_multi.csv"
combined.to_csv(output_path, index=False)
print(f"\n저장 완료: {output_path}")
print(f"최종 형태: {combined.shape[0]}행 × {combined.shape[1]}열")
print("\n[ 첫 3행 미리보기 ]")
print(combined.head(3).to_string(index=False))

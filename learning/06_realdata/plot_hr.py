import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── 1. 데이터 읽기 ────────────────────────────────────────────
hr = pd.read_csv(
    "data/4314139_heartrate.txt",
    header=None,
    names=["ts", "bpm"],
)
sleep = pd.read_csv(
    "data/4314139_labeled_sleep.txt",
    header=None,
    names=["ts", "stage"],
    sep=" ",
)

# ── 2. 수면 기록 구간만 자르기 ────────────────────────────────
# HR 타임스탬프는 -571072(기록 시작 전 수면 외 시간)까지 존재.
# Sleep 라벨은 0초부터 시작. 비교하려면 같은 구간만 봐야 함.
hr_sleep = hr[hr["ts"] >= 0].copy()

# 시간 단위 변환 (초 → 시간): x축이 "1, 2, 3시간" 으로 보이게
hr_sleep["hour"] = hr_sleep["ts"] / 3600
sleep["hour"] = sleep["ts"] / 3600

# ── 3. 이동평균 계산 ──────────────────────────────────────────
# window=30: 앞뒤 30개 측정값의 평균. 불규칙 간격이라 "30포인트" 이지만
# 대략 30분 추세를 보여줌. center=True 로 좌우 대칭 평활화.
hr_sleep["ma"] = hr_sleep["bpm"].rolling(window=30, center=True).mean()

# ── 4. 수면 단계 색상/이름 정의 ──────────────────────────────
STAGE_COLOR = {
    -1: "#cccccc",  # 기록 전/후 (회색)
     0: "#f5c842",  # Wake (노랑)
     1: "#a8d8ea",  # N1 얕은수면 (연파랑)
     2: "#4a90d9",  # N2 중간수면 (파랑)
     3: "#1a3a6e",  # N3 깊은수면 (진파랑)
     5: "#9b59b6",  # REM        (보라)
}
STAGE_LABEL = {
    -1: "Pre/Post",
     0: "Wake",
     1: "N1 (Light)",
     2: "N2 (Medium)",
     3: "N3 (Deep)",
     5: "REM",
}

# ── 5. 그래프 그리기 ──────────────────────────────────────────
# sharex=True: 두 그래프의 x축을 연결 → 하나를 확대하면 둘 다 확대됨
fig, (ax1, ax2) = plt.subplots(
    2, 1,
    figsize=(14, 8),
    sharex=True,
    gridspec_kw={"height_ratios": [3, 1]},  # 위 그래프를 3배 크게
)
fig.suptitle("Apple Watch Heart Rate + Sleep Stages (subject 4314139)", fontsize=13)

# ─ 상단: 심박수 ───────────────────────────────────────────────
# 원본: 얇고 연하게. 진짜 데이터는 이렇게 "지저분"한 게 정상.
# 어제 가짜 데이터는 sin함수처럼 매끄러웠지만, 실제 심박수는
# 숨쉬기·움직임·수면단계 변화마다 들쑥날쑥 튐.
ax1.plot(
    hr_sleep["hour"], hr_sleep["bpm"],
    color="#bbbbbb", linewidth=0.6, alpha=0.8, label="Raw HR",
)
ax1.plot(
    hr_sleep["hour"], hr_sleep["ma"],
    color="#e05555", linewidth=2.0, label="Moving Avg (30pt)",
)
ax1.set_ylabel("Heart Rate (BPM)", fontsize=11)
ax1.set_ylim(35, 185)
ax1.legend(loc="upper right", fontsize=9)
ax1.grid(True, alpha=0.25)

# ─ 하단: 수면 단계 (30초 구간마다 색 블록) ────────────────────
for i in range(len(sleep) - 1):
    stage = sleep["stage"].iloc[i]
    x0 = sleep["hour"].iloc[i]
    x1 = sleep["hour"].iloc[i + 1]
    ax2.axvspan(x0, x1, color=STAGE_COLOR.get(stage, "#ffffff"), alpha=0.85)

# 수면 단계 값을 선으로도 표시 (단계 경계가 명확하게 보이도록)
ax2.step(sleep["hour"], sleep["stage"], color="black", linewidth=0.7, where="post")
ax2.set_ylabel("Sleep Stage", fontsize=11)
ax2.set_xlabel("Elapsed Time (hours)", fontsize=11)
ax2.set_yticks([-1, 0, 1, 2, 3, 5])
ax2.set_yticklabels(["Pre/Post", "Wake", "N1", "N2", "N3", "REM"], fontsize=8)
ax2.grid(True, alpha=0.25)

# 범례
patches = [
    mpatches.Patch(color=STAGE_COLOR[k], label=STAGE_LABEL[k])
    for k in [-1, 0, 1, 2, 3, 5]
]
ax2.legend(handles=patches, loc="upper right", fontsize=8, ncol=3)

plt.tight_layout()
plt.savefig("hr_real.png", dpi=150, bbox_inches="tight")
print("저장 완료: hr_real.png")

# ── 6. 수면 단계별 평균 심박수 출력 ──────────────────────────
# merge_asof: 시간 기준으로 가장 가까운 값끼리 합치는 함수.
# 두 데이터의 타임스탬프가 딱 맞아 떨어지지 않을 때 쓰는 "근사 병합".
# 어제 가짜 데이터는 행 번호가 같아 그냥 붙일 수 있었지만,
# 진짜 데이터는 측정 시점이 달라 이렇게 해야 함.
hr_sorted = hr_sleep.sort_values("ts")
sleep_sorted = sleep.sort_values("ts")

# sleep의 ts가 int64, hr의 ts가 float64 → 타입을 맞춰야 merge_asof 작동
sleep_sorted["ts"] = sleep_sorted["ts"].astype(float)
merged = pd.merge_asof(
    hr_sorted,
    sleep_sorted[["ts", "stage"]],
    on="ts",
    direction="backward",  # HR 시점 직전의 수면 단계를 붙임
)

print("\n[ Avg HR by Sleep Stage ]")
summary = (
    merged.groupby("stage")["bpm"]
    .agg(["mean", "min", "max", "count"])
    .rename(columns={"mean": "Avg BPM", "min": "Min", "max": "Max", "count": "Count"})
)
summary.index = summary.index.map(lambda s: STAGE_LABEL.get(s, str(s)))
print(summary.round(1))
print("\n→ If N3(Deep) avg is lowest, sleep architecture is normal.")

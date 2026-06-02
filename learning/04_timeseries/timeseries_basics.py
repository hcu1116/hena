# =============================================================
# 시계열 데이터 & matplotlib 시각화
# HENA 심박수 데이터로 이동평균과 그래프 그리기
# =============================================================
# WSL 환경 주의: 화면에 창을 띄울 수 없으므로
# matplotlib 백엔드를 'Agg'(파일 저장 전용)로 설정해야 함
# → 이 줄이 없으면 "cannot connect to display" 에러 발생
import matplotlib
matplotlib.use('Agg')   # 반드시 pyplot import 전에 호출해야 함

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# =============================================================
# 1. 하루치 심박수 시계열 데이터 (기면증 환자 패턴 가정)
# =============================================================
print("=" * 48)
print("1. 시계열 데이터 생성")
print("=" * 48)

# 시계열(time series): 시간 순서대로 기록된 데이터.
# 웨어러블 데이터는 대부분 시계열. "언제" 라는 정보가 핵심.
times = [
    "06:00", "07:00", "08:00", "09:00", "10:00",
    "11:00", "12:00", "13:00", "14:00", "15:00",
    "16:00", "17:00", "18:00", "19:00", "20:00",
    "21:00", "22:00", "23:00", "00:00", "01:00",
]

# 기면증 환자의 하루 심박수 (EDS 에피소드, 탈력발작 전후 변화 반영)
# 실제 패턴처럼: 아침 안정 → 낮 EDS로 급등락 → 밤 수면 중 불규칙
heart_rates = [
    68, 72,           # 06~07시: 기상 직후, 낮음
    112, 95,          # 08~09시: EDS 에피소드, 급등
    74, 78,           # 10~11시: 잠시 안정
    105, 88,          # 12~13시: 점심 후 다시 상승
    118, 92,          # 14~15시: 오후 EDS, 최고점
    80, 76,           # 16~17시: 약간 안정
    98, 109,          # 18~19시: 저녁 불안정
    85, 70,           # 20~21시: 저녁 안정
    102, 88,          # 22~23시: 수면 진입 전 불규칙
    75, 71,           # 00~01시: 수면 중
]

df = pd.DataFrame({"time": times, "heart_rate": heart_rates})
print(df.to_string(index=False))   # index=False: 왼쪽 번호 숨김


# =============================================================
# 2. 이동평균 (Moving Average) 계산
# =============================================================
print("\n" + "=" * 48)
print("2. 이동평균 계산 (window=5)")
print("=" * 48)

# ── 이동평균이 왜 필요한가? ──────────────────────────────────
# 실제 센서 데이터에는 노이즈(순간적인 튀는 값)가 항상 섞임.
# 예: 팔을 갑자기 움직이면 심박수가 순간 튀었다가 돌아옴.
#
# 이동평균: 현재 시점 앞뒤 N개의 값을 평균 내서 노이즈를 부드럽게 만듦.
# 윈도우 크기(window)가 클수록 더 부드럽지만, 변화에 늦게 반응함.
#
# C로 직접 짜면:
#   int window = 5;
#   for (int i = window-1; i < n; i++) {
#       float sum = 0;
#       for (int j = 0; j < window; j++) sum += hr[i-j];
#       ma[i] = sum / window;
#   }
#
# pandas는 .rolling(window).mean() 한 줄로 끝:

WINDOW = 5   # 앞뒤 5개 포인트를 평균 → 처음 4개는 값 부족으로 NaN

df["moving_avg"] = df["heart_rate"].rolling(window=WINDOW).mean()

# NaN: Not a Number — 계산할 수 없는 값. 처음 window-1개는 데이터 부족.
# C에서는 이런 경우 -1이나 0으로 채우곤 하는데, pandas는 NaN으로 명시.
print(df[["time", "heart_rate", "moving_avg"]].round(1).to_string(index=False))
print(f"\n처음 {WINDOW-1}개는 NaN (앞 데이터 부족) → 그래프에서 뒤쪽만 그려짐")


# =============================================================
# 3. matplotlib으로 그래프 그리기
# =============================================================
print("\n" + "=" * 48)
print("3. 그래프 생성 중...")
print("=" * 48)

# figure: 그림 전체 캔버스. figsize=(가로인치, 세로인치).
fig, ax = plt.subplots(figsize=(12, 5))

# x축: 시간 인덱스 (0, 1, 2, ... 19) — 문자열 시간은 직접 좌표로 못 씀
x = range(len(df))

# ── 원본 심박수: 점선(linestyle='--'), 반투명(alpha), 마커(o) ──
ax.plot(
    x,
    df["heart_rate"],
    linestyle="--",          # 점선: 노이즈 있는 원본임을 시각적으로 표현
    color="#f0784b",         # HENA 코랄 색 (경고/강조)
    alpha=0.7,               # 70% 불투명도 — 이동평균 선과 겹쳐도 구분됨
    marker="o",              # 각 데이터 포인트에 원 마커
    markersize=4,
    label="Raw HR",
)

# ── 이동평균: 실선, 굵게 ──────────────────────────────────
ax.plot(
    x,
    df["moving_avg"],
    linestyle="-",           # 실선: 부드럽게 처리된 신호
    color="#0d7d7d",         # HENA 청록 색 (신뢰/안정)
    linewidth=2.5,           # 원본보다 굵게 → 주목도 높임
    label=f"Moving Avg (window={WINDOW})",
)

# ── 빈맥 기준선 (100 BPM) ───────────────────────────────
ax.axhline(
    y=100,
    color="#e53e3e",
    linestyle=":",           # 점점선
    linewidth=1.2,
    alpha=0.8,
    label="Tachycardia threshold (100 BPM)",
)

# ── 축 레이블과 눈금 설정 ────────────────────────────────
ax.set_xticks(x)
ax.set_xticklabels(df["time"], rotation=45, ha="right", fontsize=8)
ax.set_ylabel("Heart Rate (BPM)", fontsize=11)
ax.set_xlabel("Time", fontsize=11)
ax.set_title("HENA — Narcolepsy Patient Daily Heart Rate\nRaw vs Moving Average (window=5)", fontsize=13)

# ── 범례, 그리드 ─────────────────────────────────────────
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)          # y축 그리드만, 옅게
ax.set_ylim(55, 130)                  # y축 범위 고정

fig.tight_layout()   # 레이블이 잘리지 않게 여백 자동 조정


# =============================================================
# 4. PNG 파일로 저장
# =============================================================
import os
output_path = os.path.join(os.path.dirname(__file__), "hr_plot.png")
fig.savefig(output_path, dpi=150, bbox_inches="tight")
plt.close(fig)   # 메모리 해제 (창을 열지 않으므로 항상 close 호출)

print(f"그래프 저장 완료: {output_path}")
print("\n✅ 완료!")

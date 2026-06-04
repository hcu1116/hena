import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# ══════════════════════════════════════════════════════════════
# 이 파일이 train_model.py와 다른 핵심 두 가지
#
# ① 데이터가 7명 (지난번: 1명)
# ② train/test 분리를 "사람 단위"로 함 (지난번: 랜덤 80/20)
#
# 왜 사람 단위로 분리하는가?
#   랜덤 분리: 같은 사람의 창이 train과 test에 둘 다 섞임.
#     → 모델이 "이 사람은 심박이 55bpm대구나"라는 개인 특성을 이미 알고 평가.
#     → 점수가 실제보다 높아짐 (data leakage의 약한 형태).
#
#   사람 단위 분리: test 사람의 창은 학습에 한 번도 쓰이지 않음.
#     → 모델이 처음 보는 사람에서 얼마나 맞히는가 = 진짜 일반화 성능.
#     → 실제 앱으로 출시하면 항상 이 상황: 새 사용자가 착용.
# ══════════════════════════════════════════════════════════════

FEATURES     = ["hr_mean", "hr_std", "accel_mean", "accel_std"]
STAGE_NAME   = {0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}
PREV_RF_ACC  = 0.689   # train_model.py 결과 (1명, 랜덤 분리)

# ── 1. 데이터 읽기 ────────────────────────────────────────────
df = pd.read_csv("prepared_multi.csv")
df["subject_id"] = df["subject_id"].astype(str)

subjects = sorted(df["subject_id"].unique())
print(f"데이터: {len(df)}행 × {len(df.columns)}열, 피험자 {len(subjects)}명")
print(f"피험자 목록: {subjects}\n")

# ── 2. 사람 단위 train/test 분리 ──────────────────────────────
#
# 누구를 test로 쓸까?
#   - 창이 너무 적으면 평가가 불안정 → 1455390(138창), 3509524(161창) 제외
#   - 수면 단계가 다양해야 평가가 풍부 → 5가지 단계 모두 있는 사람 우선
#   - 2638030: 800창, Wake/N1/N2/N3/REM 모두 있음 → 선택
#
# 나중에 이 변수만 바꾸면 다른 사람으로 test 가능.
TEST_SUBJECT = "2638030"

train_df = df[df["subject_id"] != TEST_SUBJECT].copy()
test_df  = df[df["subject_id"] == TEST_SUBJECT].copy()

print("=" * 55)
print("[ train/test 분리 — 사람 단위 ]")
print("=" * 55)
print(f"  Train: {sorted(train_df['subject_id'].unique())}")
print(f"         → {len(train_df)}개 창")
print(f"  Test:  [{TEST_SUBJECT}]")
print(f"         → {len(test_df)}개 창")
print()

# ── 3. 입력(X)과 정답(y) 분리 ────────────────────────────────
X_train = train_df[FEATURES]
y_train = train_df["stage"]
X_test  = test_df[FEATURES]
y_test  = test_df["stage"]

print(f"Train 수면 단계 분포:")
for stage, cnt in y_train.value_counts().sort_index().items():
    print(f"  {STAGE_NAME.get(stage, stage):10s} {cnt:5d}개")
print(f"\nTest ({TEST_SUBJECT}) 수면 단계 분포:")
for stage, cnt in y_test.value_counts().sort_index().items():
    print(f"  {STAGE_NAME.get(stage, stage):10s} {cnt:5d}개")

# ── 4. RandomForest 학습 ──────────────────────────────────────
#
# 왜 RandomForest?
#   지난번 비교에서 DecisionTree보다 10% 높았음.
#   결정 나무를 여러 개(n_estimators=100) 만들어 다수결.
#   각 나무가 조금씩 다른 데이터/피처 조합을 봐서 더 안정적.
#
print("\n" + "=" * 55)
print("[ RandomForest 학습 ]")
print("=" * 55)
print(f"  나무 개수: 100  |  학습 데이터: {len(X_train)}개 창")

rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
print("  학습 완료.")

# ── 5. test 사람에서 예측 ─────────────────────────────────────
y_pred = rf.predict(X_test)
acc    = accuracy_score(y_test, y_pred)

print(f"\n[ 결과: {TEST_SUBJECT}에서 정확도 = {acc:.1%} ]")

# ── 6. 단계별 상세 리포트 ─────────────────────────────────────
#
# precision (정밀도): 모델이 "N2다"라고 했을 때 실제로 N2일 확률
# recall    (재현율): 실제 N2 중에서 모델이 N2로 맞힌 비율
# f1-score         : precision과 recall의 조화평균
# support          : 해당 단계의 실제 창 수
#
# 수면 단계 예측에서 가장 어려운 단계:
#   N1 — 수면과 각성의 경계. 짧고 불규칙. 심박·가속도 차이가 미미.
#   N1의 recall이 낮은 건 웨어러블의 근본적 한계.
test_stages = sorted(y_test.unique())
target_names = [STAGE_NAME.get(s, str(s)) for s in test_stages]

print("\n[ 수면 단계별 상세 리포트 ]")
print(classification_report(
    y_test, y_pred,
    labels=test_stages,
    target_names=target_names,
    zero_division=0,
))

# ── 7. 지난번 vs 이번 비교 ────────────────────────────────────
#
# 왜 성능이 달라지는가?
#
# [경우 A: 성능 향상]
#   여러 사람의 다양한 패턴을 보고 일반적인 규칙을 학습.
#   "심박이 낮고 움직임이 없으면 깊은수면"이라는 패턴은
#   대부분의 사람에게 공통적으로 적용됨.
#
# [경우 B: 성능 하락]
#   지난번 test는 train과 같은 사람이었음 (랜덤 분리).
#   → 개인 특성(이 사람은 보통 60bpm)을 이미 알고 평가 → 유리했음.
#   이번 test는 처음 보는 사람 → 개인 특성 모름 → 더 어려운 평가.
#   즉 지난번 68.9%는 실제보다 부풀려진 수치였을 가능성이 있음.
#
# 어떤 숫자가 더 "진짜"인가?
#   이번 숫자. 실제 앱은 항상 새로운 사람을 상대하기 때문.

print("=" * 55)
print("[ 성능 비교: 1명 모델 vs 7명 모델 ]")
print("=" * 55)

models_info = [
    ("1명 모델 (지난번)", PREV_RF_ACC,
     "한 사람, 랜덤 80/20 분리"),
    (f"7명 모델 (이번)",  acc,
     f"6명 학습 → {TEST_SUBJECT} 평가"),
]

for label, score, note in models_info:
    bar  = "█" * int(score * 40)
    diff = ""
    if score != PREV_RF_ACC:
        delta = score - PREV_RF_ACC
        diff  = f"  ({'▲' if delta > 0 else '▼'}{abs(delta):.1%})"
    print(f"\n  {label}")
    print(f"  정확도: {score:.1%}{diff}")
    print(f"  조건:   {note}")
    print(f"  {bar}")

print()
print("[ 해석 가이드 ]")
if acc > PREV_RF_ACC:
    print("""
  정확도가 올랐다면:
    여러 사람을 학습해서 일반적인 수면 패턴을 더 잘 파악.
    데이터가 많을수록 ML 모델은 더 안정적인 결정 경계를 학습.
    단, test 사람(2638030)이 우연히 학습 패턴에 잘 맞을 수도 있음.
    → 다른 사람도 test로 써보는 것이 좋음 (다음 단계: 교차검증).
""")
else:
    print("""
  정확도가 내렸다면:
    이게 더 "솔직한" 숫자일 가능성이 높음.
    지난번 68.9%는 같은 사람 데이터로 평가했으므로 유리했음.
    이번엔 처음 보는 사람을 예측 → 더 어려운 조건.

    그렇다고 나쁜 모델이 된 게 아님:
    ① test 사람 수가 1명뿐 → 한 사람에 따라 결과가 크게 달라짐.
    ② 피처 4개만으로 처음 보는 사람의 수면 단계를 맞히는 건 원래 어려움.
    ③ 데이터를 더 모으고, 피처를 추가하면 개선 가능.
""")

# ── 8. 피처 중요도 ────────────────────────────────────────────
#
# 지난번과 순위가 달라졌는가?
#   한 사람 기준: 그 사람의 개인 특성에 맞는 피처가 중요하게 나왔을 수 있음.
#   여러 사람 기준: 개인 차이를 넘어 공통적으로 중요한 피처가 부각됨.
#   → 더 신뢰할 수 있는 피처 중요도.
print("=" * 55)
print("[ 피처 중요도 (여러 사람 기준) ]")
print("=" * 55)

importance = pd.Series(rf.feature_importances_, index=FEATURES).sort_values(ascending=False)
for feat, score in importance.items():
    bar = "▓" * int(score * 60)
    print(f"  {feat:15s} {score:.3f}  {bar}")

print("""
  해석:
    accel_mean이 높다면 → 움직임 평균이 수면 단계를 가르는 핵심 신호.
      (깊은수면/REM: 거의 안 움직임 / Wake: 활발히 움직임)
    hr_mean이 높다면   → 심박수 절대값이 단계 구분에 도움.
      (Wake: 높음 / 깊은수면: 낮음)
    std 계열이 높다면  → "얼마나 불규칙한가"가 중요.
      (REM: 심박 변동 큼 / 깊은수면: 안정적)
""")

# ── 9. 한계와 다음 단계 ──────────────────────────────────────
print("=" * 55)
print("[ 한계와 개선 방향 ]")
print("=" * 55)
print(f"""
  현재 한계:
    ① test가 1명뿐 → 우연히 쉬운(또는 어려운) 사람을 고른 것일 수 있음.
    ② 피험자마다 수면 시간·단계 분포가 다름 → 불균형 데이터 문제.
    ③ 피처가 4개뿐 (심박·가속도 평균·표준편차).

  다음에 시도할 것:
    → Leave-One-Out 교차검증: 7번 반복, 매번 다른 1명을 test로
       → 7명 각각에서 정확도 → 평균/분산으로 안정적 성능 파악
    → 피처 추가: 심박 변동성(HRV), 이동 범위, 구간별 추세 등
    → 클래스 불균형 보정: N1이 너무 적어서 모델이 N1을 무시하는 경향
""")

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# ══════════════════════════════════════════════════════════════
# Leave-One-Out 교차검증 (LOOCV) — 원리
#
# 문제: train_multi.py에서 한 사람(2638030)만 test로 썼다.
#       운 좋게 쉬운 사람을 골랐다면 점수가 높게 나오고,
#       어려운 사람을 골랐다면 낮게 나온다.
#       → 어떤 숫자가 "진짜" 성능인지 알 수 없다.
#
# 해결: 모든 사람을 한 번씩 test로 써서 점수 7개를 모두 구한다.
#
#   Round 1: train=[A,B,C,D,E,F]  test=[G]  → 정확도_G
#   Round 2: train=[A,B,C,D,E,G]  test=[F]  → 정확도_F
#   ...
#   Round 7: train=[B,C,D,E,F,G]  test=[A]  → 정확도_A
#
#   평균(정확도_A ~ 정확도_G) = 운이 제거된 "진짜 일반화 성능"
#
# 이 방법의 장점:
#   - 모든 데이터가 한 번씩 평가에 쓰임 → 낭비 없음
#   - 특정 사람 하나에 좌우되지 않는 안정적인 성능 추정
#   - "평균 X%, 최저 Y%, 최고 Z%"로 신뢰 구간을 표현 가능
# ══════════════════════════════════════════════════════════════

FEATURES   = ["hr_mean", "hr_std", "accel_mean", "accel_std"]
STAGE_NAME = {0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}

# ── 1. 데이터 읽기 ────────────────────────────────────────────
df = pd.read_csv("prepared_multi.csv")
df["subject_id"] = df["subject_id"].astype(str)
subjects = sorted(df["subject_id"].unique())

print("=" * 60)
print("[ Leave-One-Out 교차검증 시작 ]")
print(f"  피험자 {len(subjects)}명, 총 {len(df)}개 창")
print(f"  반복 횟수: {len(subjects)}번 (각 사람이 한 번씩 test)")
print("=" * 60)

# ── 2. LOO-CV 메인 루프 ───────────────────────────────────────
results = []   # 각 round 결과를 여기에 쌓을 리스트

for i, test_subject in enumerate(subjects, 1):
    # 사람 단위 분리 — train_multi.py와 동일한 원리
    train_df = df[df["subject_id"] != test_subject]
    test_df  = df[df["subject_id"] == test_subject]

    X_train = train_df[FEATURES]
    y_train = train_df["stage"]
    X_test  = test_df[FEATURES]
    y_test  = test_df["stage"]

    # RandomForest 학습 및 예측
    # n_jobs=-1: 가능한 모든 CPU 코어 사용 → 7번 반복해도 빠름
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)

    acc = accuracy_score(y_test, y_pred)

    # 단계별 f1 점수 (단계가 없는 경우 0으로 처리)
    # zero_division=0: test에 없는 단계는 점수가 0
    report = classification_report(
        y_test, y_pred,
        labels=sorted(y_test.unique()),
        output_dict=True,   # dict로 받아 나중에 분석에 사용
        zero_division=0,
    )

    # 이 사람의 특성을 함께 기록 (나중에 "왜 점수가 다른가" 분석에 사용)
    n_windows  = len(test_df)
    n_stages   = test_df["stage"].nunique()   # 몇 가지 수면 단계가 있는가
    stages_present = sorted(test_df["stage"].unique())

    results.append({
        "subject_id":      test_subject,
        "accuracy":        acc,
        "n_windows":       n_windows,
        "n_stages":        n_stages,
        "stages_present":  stages_present,
        "report":          report,
        "y_test":          y_test,
        "y_pred":          y_pred,
    })

    # 진행 상황 간단 출력
    stage_str = "/".join(STAGE_NAME.get(s, str(s)) for s in stages_present)
    print(f"  [{i}/{len(subjects)}] {test_subject}  "
          f"정확도: {acc:.1%}  창: {n_windows}  단계: {stage_str}")

# ── 3. 결과 테이블 ────────────────────────────────────────────
print("\n" + "=" * 60)
print("[ 피험자별 정확도 전체 표 ]")
print("=" * 60)
print(f"  {'subject':>10}  {'정확도':>6}  {'창 수':>6}  {'단계 수':>6}  {'막대그래프'}")
print(f"  {'-'*10}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*30}")

accs = [r["accuracy"] for r in results]
for r in results:
    bar  = "█" * int(r["accuracy"] * 30)
    mark = ""
    if r["accuracy"] == max(accs):
        mark = " ← 최고"
    elif r["accuracy"] == min(accs):
        mark = " ← 최저"
    print(f"  {r['subject_id']:>10}  {r['accuracy']:>6.1%}  "
          f"{r['n_windows']:>6}  {r['n_stages']:>6}  {bar}{mark}")

# ── 4. 전체 통계 ──────────────────────────────────────────────
mean_acc = np.mean(accs)
std_acc  = np.std(accs)
min_acc  = np.min(accs)
max_acc  = np.max(accs)

print(f"\n  평균:  {mean_acc:.1%}  ← '이 모델이 새 사람한테 평균 몇 %?'에 대한 답")
print(f"  표준편차: {std_acc:.1%}  ← 숫자가 클수록 사람마다 결과가 들쭉날쭉")
print(f"  최저:  {min_acc:.1%}  /  최고: {max_acc:.1%}")
print(f"  범위:  {min_acc:.1%} ~ {max_acc:.1%}  "
      f"({max_acc - min_acc:.1%} 차이)")

# ── 5. 단계별 F1 전체 표 ──────────────────────────────────────
# F1-score를 단계별로 정리 — 어떤 단계가 일관적으로 어려운지 파악
print("\n" + "=" * 60)
print("[ 수면 단계별 F1-score (사람별) ]")
print("=" * 60)

all_stages = sorted({s for r in results for s in r["stages_present"]})
header = f"  {'subject':>10}  " + "  ".join(f"{STAGE_NAME.get(s,'?'):>9}" for s in all_stages)
print(header)
print(f"  {'-'*10}  " + "  ".join(f"{'-'*9}" for _ in all_stages))

for r in results:
    row = f"  {r['subject_id']:>10}  "
    for s in all_stages:
        s_str = str(s)
        if s_str in r["report"]:
            f1 = r["report"][s_str]["f1-score"]
            row += f"{f1:>9.2f}  "
        else:
            row += f"{'(없음)':>9}  "   # 이 사람에게 없는 단계
    print(row)

# 단계별 평균 F1
print(f"\n  {'평균':>10}  ", end="")
for s in all_stages:
    s_str = str(s)
    vals  = [r["report"][s_str]["f1-score"]
             for r in results if s_str in r["report"]]
    print(f"{np.mean(vals):>9.2f}  ", end="")
print()

# ── 6. "왜 사람마다 점수가 다른가?" 분석 ─────────────────────
#
# 가설 A: 창이 많을수록 점수가 높다?
#   → 훈련 데이터에 없던 패턴이 이 사람에게 많을 수 있음.
#     반대로, 창이 적은 사람은 특이한 수면 패턴일 가능성이 있음.
#
# 가설 B: 수면 단계가 다양할수록 점수가 낮다?
#   → 맞혀야 할 단계가 많을수록 어렵기 때문.
#     5단계보다 3단계를 맞히는 게 당연히 쉬움.
#
# 가설 C: 특정 단계(N3, N1)가 있으면 점수가 낮다?
#   → N3와 N1이 심박·가속도로 구분하기 제일 어려운 단계.
print("\n" + "=" * 60)
print("[ 사람마다 정확도가 다른 이유 — 데이터 기반 분석 ]")
print("=" * 60)

# 창 수 vs 정확도 상관
n_wins = [r["n_windows"] for r in results]
corr_n = np.corrcoef(n_wins, accs)[0, 1]
print(f"\n  창 수 ↔ 정확도 상관계수: {corr_n:+.3f}")
if abs(corr_n) < 0.3:
    print("  → 창이 많다고 점수가 높아지는 건 아님.")
elif corr_n > 0:
    print("  → 창이 많을수록 점수가 약간 높은 경향이 있음.")
else:
    print("  → 창이 많을수록 오히려 점수가 낮은 경향. (특이한 패턴이 많을 수 있음)")

# 단계 수 vs 정확도 상관
n_stgs = [r["n_stages"] for r in results]
corr_s = np.corrcoef(n_stgs, accs)[0, 1]
print(f"\n  단계 수 ↔ 정확도 상관계수: {corr_s:+.3f}")
if corr_s < -0.3:
    print("  → 맞혀야 할 단계가 많을수록 점수가 낮아지는 경향이 있음.")
elif abs(corr_s) < 0.3:
    print("  → 단계 수는 정확도에 큰 영향을 미치지 않음.")
else:
    print("  → 단계가 다양해도 점수가 높을 수 있음.")

# N3 유무와 정확도
has_n3   = [3 in r["stages_present"] for r in results]
n3_accs  = [r["accuracy"] for r in results if 3 in r["stages_present"]]
no_n3    = [r["accuracy"] for r in results if 3 not in r["stages_present"]]
print(f"\n  N3 있는 사람 평균 정확도: {np.mean(n3_accs):.1%}  ({len(n3_accs)}명)")
if no_n3:
    print(f"  N3 없는 사람 평균 정확도: {np.mean(no_n3):.1%}  ({len(no_n3)}명)")
    diff = np.mean(n3_accs) - np.mean(no_n3)
    if diff < -0.03:
        print(f"  → N3가 있으면 {abs(diff):.1%} 더 어렵다. (N3 ↔ N2 혼동이 많아서)")
    elif diff > 0.03:
        print(f"  → N3가 있는 사람이 오히려 높음. (다른 요인이 더 영향을 줌)")
    else:
        print("  → N3 유무에 따른 차이가 크지 않음.")

# 개인별 상세 설명
print(f"\n  [ 개인별 분석 ]")
sorted_results = sorted(results, key=lambda r: r["accuracy"], reverse=True)
for r in sorted_results:
    notes = []
    if r["n_windows"] < 200:
        notes.append("창 수 적음(측정 짧음)")
    if 3 not in r["stages_present"]:
        notes.append("N3 없음")
    if 5 not in r["stages_present"]:
        notes.append("REM 없음")
    if r["n_stages"] <= 3:
        notes.append("단계 단순(3종류)")
    note_str = " / ".join(notes) if notes else "기본 조건"
    print(f"  {r['subject_id']:>10}  {r['accuracy']:.1%}  ← {note_str}")

# ── 7. 지난번 실험들과 최종 비교 ─────────────────────────────
print("\n" + "=" * 60)
print("[ 지금까지 세 가지 실험 비교 ]")
print("=" * 60)
print(f"""
  실험 1 — 1명, 랜덤 분리 (train_model.py)
    조건:  4314139 한 명, 80%로 학습, 20%(같은 사람)로 평가
    정확도: 68.9%
    문제:  같은 사람 데이터로 평가 → 개인 특성을 이미 알고 있음
           → 실제 성능보다 높게 보임

  실험 2 — 7명, 1명을 test (train_multi.py)
    조건:  6명으로 학습, 2638030(처음 보는 사람)으로 평가
    정확도: 56.6%
    문제:  test 사람이 1명이라 운에 좌우됨
           2638030이 우연히 어려운 사람이었을 수도 있음

  실험 3 — 7명, Leave-One-Out 교차검증 (이 파일)
    조건:  모든 사람을 한 번씩 test로 돌아가며 평가
    정확도: 평균 {mean_acc:.1%}  (범위: {min_acc:.1%} ~ {max_acc:.1%})
    의미:  운이 제거된 가장 신뢰할 수 있는 성능 추정값
           "이 모델은 새 사람에게 평균 {mean_acc:.1%} 정확도로 통한다"
""")

# ── 8. 연구 논문에서 보고되는 실제 성능 기준 ─────────────────
print("=" * 60)
print("[ 현재 모델 수준 — 실제 연구와 비교 ]")
print("=" * 60)
print(f"""
  현재 모델:  평균 {mean_acc:.1%}  (피처 4개, 손목 가속도+심박)

  학계 벤치마크 (웨어러블 수면 단계 예측):
    4단계 분류:  약 68~78%  (삼성, Apple Watch 관련 논문)
    5단계 분류:  약 57~68%  (PSG 라벨 기준)

  → 논문들은 훨씬 많은 피처를 씀:
      심박 변동성(HRV), SpO2, 피부 온도, 수면 이전 활동량 등
  → 피처 4개로 이 수준이면 시작점으로는 나쁘지 않음.
  → 다음 목표: 피처를 추가해서 {mean_acc + 0.05:.1%} 이상으로 올리기
""")

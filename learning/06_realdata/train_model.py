import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# ── 1. 데이터 읽기 ────────────────────────────────────────────
df = pd.read_csv("prepared.csv")

print(f"데이터: {df.shape[0]}행 × {df.shape[1]}열")
print(f"수면 단계 분포:\n{df['stage'].value_counts().sort_index()}\n")

# ── 2. 입력(X)과 정답(y) 분리 ────────────────────────────────
# X: 모델이 "보는" 정보. 웨어러블이 측정한 값들.
# y: 모델이 "맞혀야 하는" 정답. PSG로 측정한 실제 수면 단계.
#
# ts(타임스탬프)는 "몇 번째 창인가"일 뿐, 수면 단계를 예측하는
# 의미 있는 정보가 아니어서 제외.
FEATURES = ["hr_mean", "hr_std", "accel_mean", "accel_std"]
X = df[FEATURES]
y = df["stage"]

# ── 3. train / test 분리 ──────────────────────────────────────
# 어제 배운 원칙: 모델이 "본 데이터"로 평가하면 시험지 답 외운 것.
# test_size=0.2 → 20%는 평가용, 80%는 학습용.
# random_state=42 → 분리 방식을 고정해서 실행할 때마다 같은 결과.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"학습용: {len(X_train)}행 / 평가용: {len(X_test)}행\n")

# ── 4. 모델 두 개 정의 ────────────────────────────────────────
# DecisionTree: 질문을 나무처럼 분기해서 분류.
#   "심박 평균이 65 미만이면 → 깊은수면 or N2?"
#   단순하고 해석하기 쉬움. 하지만 과적합(학습 데이터에만 잘 맞음)이 쉬움.
#
# RandomForest: DecisionTree를 수백 개 만들어 다수결로 결정.
#   각 나무가 조금씩 다른 데이터/피처 조합을 봄.
#   더 안정적이고 정확하지만 "왜 이 예측을 했는가"가 불투명해짐.
models = {
    "DecisionTree": DecisionTreeClassifier(random_state=42),
    "RandomForest": RandomForestClassifier(n_estimators=100, random_state=42),
}

STAGE_NAME = {0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}

# ── 5. 학습 → 평가 → 리포트 ──────────────────────────────────
results = {}
for name, model in models.items():
    # fit(): 학습. X_train의 패턴과 y_train의 정답을 연결하는 과정.
    model.fit(X_train, y_train)

    # predict(): 예측. X_test만 보고 수면 단계를 추측.
    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    results[name] = (y_test, y_pred, acc)

    print("=" * 55)
    print(f"[{name}]  정확도: {acc:.1%}")
    print("=" * 55)

    # classification_report: 단계별 정밀도/재현율/F1 한 눈에
    # precision: 모델이 "N2다" 했을 때 실제로 N2일 확률
    # recall:    실제 N2 중에서 모델이 N2로 맞힌 비율
    # f1-score:  precision과 recall의 조화평균 (둘 다 높아야 높음)
    report = classification_report(
        y_test, y_pred,
        target_names=[STAGE_NAME[s] for s in sorted(y.unique())],
        zero_division=0,
    )
    print(report)

# ── 6. 두 모델 비교 요약 ──────────────────────────────────────
print("=" * 55)
print("[ 최종 비교 ]")
for name, (_, _, acc) in results.items():
    bar = "█" * int(acc * 40)
    print(f"  {name:15s} {acc:.1%}  {bar}")

# ── 7. 정확도가 100%가 아닌 이유 ─────────────────────────────
print("""
[ 왜 정확도가 100%가 안 나오는가 ]

① 피처가 부족하다
   심박수 평균·표준편차, 가속도만으로는 정보가 부족.
   뇌파(EEG), 안구운동(EOG), 혈중산소 등이 있으면 훨씬 정확해짐.
   웨어러블의 근본적 한계 — 손목 데이터로 뇌 상태를 추측하는 것.

② 데이터가 적다
   한 사람의 하룻밤 = 610개 창. ML에겐 매우 작은 양.
   10~100명 데이터를 합쳐야 일반화 가능.

③ 수면 단계 경계는 원래 모호하다
   N2→N3는 전문가도 판단이 엇갈리는 경우가 있음.
   정답 라벨 자체가 불완전할 수 있음.

④ 100%가 나오면 오히려 의심해야 한다
   test 데이터가 train에 새어들어갔거나(data leakage),
   라벨을 피처로 쓰는 실수가 있을 때 일어남.
""")

# ── 8. 피처 중요도 (RandomForest) ────────────────────────────
# RandomForest는 어떤 피처가 결정에 많이 쓰였는지 계산해줌.
rf = models["RandomForest"]
importance = pd.Series(rf.feature_importances_, index=FEATURES)
print("[ RandomForest 피처 중요도 ]")
for feat, score in importance.sort_values(ascending=False).items():
    bar = "▓" * int(score * 50)
    print(f"  {feat:15s} {score:.3f}  {bar}")

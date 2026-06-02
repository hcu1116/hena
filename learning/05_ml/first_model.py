# =============================================================
# 첫 번째 머신러닝 모델 — 기면증 의심 분류기
# scikit-learn 입문
# =============================================================
# 목표: 웨어러블 데이터(HR, 수면시간, 낮졸림) 3가지를 보고
#       "이 사람이 기면증 의심인지 아닌지" 분류하는 모델 만들기
# =============================================================

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# =============================================================
# STEP 1. 데이터 생성
# =============================================================
# 머신러닝의 핵심 개념 두 가지:
#
# Feature(특징): 모델에 입력하는 정보. 여기선 웨어러블 측정값 3개.
#   - avg_hr      : 평균 심박수 (BPM)
#   - sleep_hours : 평균 수면 시간
#   - eds_score   : 낮졸림 점수 (0~10, 높을수록 졸림)
#
# Label(정답): 모델이 맞춰야 하는 답.
#   - 0: 정상
#   - 1: 기면증 의심
#
# 지금은 실제 데이터가 없으니 의학 패턴을 반영한 가짜 데이터를 만듦.
# 나중에 실제 데이터셋이 생기면 이 부분만 교체하면 됨.

print("=" * 52)
print("STEP 1. 데이터 생성 (80명)")
print("=" * 52)

rng = np.random.default_rng(seed=42)   # seed: 실행할 때마다 같은 난수 나오게 고정

# ── 정상인 50명 ──────────────────────────────────────────────
# 패턴: HR 낮음, 수면 충분, 졸림 낮음
n_normal = 50
normal = {
    "avg_hr":      rng.normal(loc=70, scale=5,   size=n_normal),  # 평균 70 BPM
    "sleep_hours": rng.normal(loc=7.2, scale=0.7, size=n_normal), # 평균 7.2시간
    "eds_score":   rng.normal(loc=3.0, scale=1.2, size=n_normal), # 평균 3점 (낮은 졸림)
    "label":       np.zeros(n_normal, dtype=int),                  # 정답: 0 (정상)
}

# ── 기면증 의심 30명 ─────────────────────────────────────────
# 패턴: HR 높음(자율신경 이상), 수면 짧거나 분절, 졸림 높음
n_narco = 30
narco = {
    "avg_hr":      rng.normal(loc=85, scale=8,   size=n_narco),   # 평균 85 BPM (높음)
    "sleep_hours": rng.normal(loc=5.5, scale=1.0, size=n_narco),  # 평균 5.5시간 (짧음)
    "eds_score":   rng.normal(loc=7.5, scale=1.2, size=n_narco),  # 평균 7.5점 (높은 졸림)
    "label":       np.ones(n_narco, dtype=int),                    # 정답: 1 (의심)
}

# 두 그룹을 하나의 DataFrame으로 합치기 (지난 시간에 배운 pandas)
df = pd.concat([
    pd.DataFrame(normal),
    pd.DataFrame(narco),
]).round(1).reset_index(drop=True)

print(f"전체 데이터: {len(df)}명")
print(f"  정상(0): {(df['label']==0).sum()}명")
print(f"  의심(1): {(df['label']==1).sum()}명")
print(f"\n처음 5줄 미리보기:")
print(df.head())


# =============================================================
# STEP 2. Feature(X)와 Label(y) 분리
# =============================================================
# 관례적으로:
#   X = Feature 행렬 (입력, 대문자)
#   y = Label 벡터  (정답, 소문자)
# C 비유: X는 입력 배열, y는 정답 배열.

print("\n" + "=" * 52)
print("STEP 2. X(특징) / y(정답) 분리")
print("=" * 52)

X = df[["avg_hr", "sleep_hours", "eds_score"]]   # Feature 3개 열
y = df["label"]                                   # Label 1개 열

print(f"X shape: {X.shape}  → (사람 수, feature 수)")
print(f"y shape: {y.shape}  → (사람 수,)")


# =============================================================
# STEP 3. Train / Test 분리 ← 가장 중요한 개념
# =============================================================
# 왜 나누는가?
#
#   시험 공부 비유:
#   - train 데이터 = 문제집 (모델이 여기서 패턴을 익힘)
#   - test  데이터 = 실제 시험 (한 번도 본 적 없는 문제)
#
#   만약 test를 안 쓰고 train으로만 평가하면?
#   → "이미 본 문제"라 100% 나올 수 있음 = 암기한 것, 이해한 게 아님.
#   → 실제 새 데이터엔 형편없을 수도 있음 (과적합, overfitting)
#
#   test_size=0.2 : 전체 중 20%를 시험용으로 따로 보관
#   random_state=42: 매번 같은 방식으로 나누도록 고정 (재현성)

print("\n" + "=" * 52)
print("STEP 3. Train / Test 분리 (8:2)")
print("=" * 52)

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,     # 20%는 test → 16명 / 80%는 train → 64명
    random_state=42,
    stratify=y,        # 정상:의심 비율을 train/test에서 동일하게 유지
)

print(f"Train(공부용): {len(X_train)}명  ← 모델이 이걸로 패턴을 배움")
print(f"Test (시험용): {len(X_test)}명   ← 학습 후 여기서 성능 평가")


# =============================================================
# STEP 4. 모델 선택 및 학습
# =============================================================
# DecisionTree(결정 트리)를 고른 이유:
#   가장 이해하기 쉬운 모델. 내부 논리가 if/else 조건문의 연속.
#   예: "eds_score > 6이면 → 의심, 아니면 → HR 확인..."
#   블랙박스가 아니라 "왜 그런 결론을 냈는지" 직접 볼 수 있음.
#
# max_depth=3: 트리 깊이(질문 단계)를 최대 3으로 제한.
#   너무 깊으면 train 데이터에 과적합됨.

print("\n" + "=" * 52)
print("STEP 4. 모델 학습")
print("=" * 52)

model = DecisionTreeClassifier(max_depth=3, random_state=42)

# .fit() = 학습. train 데이터를 모델에게 보여주며 패턴을 찾게 함.
# C 비유: 함수를 "훈련"시키는 것. 이후 .predict()로 사용.
model.fit(X_train, y_train)

print("학습 완료.")
print(f"사용된 feature: {list(X.columns)}")


# =============================================================
# STEP 5. 평가 — test 데이터로 정확도 측정
# =============================================================
# 정확도(accuracy) = 맞게 예측한 수 / 전체 수
# 예: 16명 중 14명 맞추면 → 14/16 = 87.5%
#
# 주의: 정확도만으로 모델을 판단하면 안 됨 (이건 나중에 배울 내용).
# 지금 단계에서는 "숫자가 어떻게 나오는가"를 이해하는 게 목표.

print("\n" + "=" * 52)
print("STEP 5. 성능 평가")
print("=" * 52)

y_pred = model.predict(X_test)   # test 데이터의 정답을 모르는 척하고 예측

accuracy = accuracy_score(y_test, y_pred)
print(f"Test 정확도: {accuracy:.1%}")   # .1% : 소수점 1자리 퍼센트

# 예측값 vs 실제 정답 나란히 보기
result_df = X_test.copy()
result_df["실제"] = y_test.values
result_df["예측"] = y_pred
result_df["맞음"] = (y_test.values == y_pred)
print(f"\n예측 결과 (test {len(X_test)}명):")
print(result_df.to_string(index=False))


# =============================================================
# STEP 6. 새 사람 예측
# =============================================================
# 학습된 모델로 완전히 새로운 사람을 예측해보기.
# 이게 실제 HENA가 하려는 것: 웨어러블 데이터 → 위험도 예측

print("\n" + "=" * 52)
print("STEP 6. 새 사람 예측")
print("=" * 52)

new_people = pd.DataFrame({
    "avg_hr":      [88,  68],
    "sleep_hours": [5.0, 7.5],
    "eds_score":   [8.2, 2.5],
}, index=["김철수(의심)", "이영희(정상)"])

predictions = model.predict(new_people)
label_map = {0: "정상", 1: "기면증 의심"}

for name, pred in zip(new_people.index, predictions):
    row = new_people.loc[name]
    print(f"  {name}")
    print(f"    HR={row['avg_hr']}, 수면={row['sleep_hours']}h, 졸림={row['eds_score']}점")
    print(f"    → 예측: {label_map[pred]}")


# =============================================================
# STEP 7. 모델이 배운 규칙 보기 (Decision Tree의 장점)
# =============================================================
# 이 트리가 실제로 어떤 질문을 하는지 출력.
# 다른 모델(신경망 등)은 이런 해석이 불가능함.

print("\n" + "=" * 52)
print("STEP 7. 모델이 배운 if/else 규칙")
print("=" * 52)
print(export_text(model, feature_names=list(X.columns)))
print("(읽는 법: <= 조건이 True면 왼쪽, False면 오른쪽 / class가 최종 예측)")

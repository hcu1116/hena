import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# ══════════════════════════════════════════════════════════════
# HRV 피처 추가 전/후 비교 실험
#
# 방법: LOO-CV를 두 번 돌린다.
#   실험 A — 기존 4개 피처 (hr_mean, hr_std, accel_mean, accel_std)
#   실험 B — 기존 4개 + HRV 3개 (hrv_rmssd, hrv_sdnn, hrv_pnn50)
#
# 비교 포인트:
#   1. 전체 평균 정확도: HRV가 도움이 됐는가?
#   2. 단계별 F1: 어떤 단계에서 개선됐는가?
#   3. 피처 중요도: HRV 3개 중 어느 것이 가장 유용했는가?
# ══════════════════════════════════════════════════════════════

FEATURES_BASE = ["hr_mean", "hr_std", "accel_mean", "accel_std"]
FEATURES_HRV  = ["hr_mean", "hr_std", "accel_mean", "accel_std",
                  "hrv_rmssd", "hrv_sdnn", "hrv_pnn50"]

STAGE_NAME = {0: "Wake", 1: "N1", 2: "N2", 3: "N3(Deep)", 5: "REM"}


def run_loocv(df: pd.DataFrame, features: list[str], label: str) -> dict:
    """LOO-CV를 실행하고 결과를 반환."""
    subjects = sorted(df["subject_id"].unique())

    print(f"\n{'─'*60}")
    print(f"[ {label} ]")
    print(f"  피처: {features}")
    print(f"{'─'*60}")

    results = []
    all_importances = []

    for i, test_subject in enumerate(subjects, 1):
        train_df = df[df["subject_id"] != test_subject]
        test_df  = df[df["subject_id"] == test_subject]

        X_train = train_df[features]
        y_train = train_df["stage"]
        X_test  = test_df[features]
        y_test  = test_df["stage"]

        rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        report = classification_report(
            y_test, y_pred,
            labels=sorted(y_test.unique()),
            output_dict=True,
            zero_division=0,
        )

        results.append({
            "subject_id":     test_subject,
            "accuracy":       acc,
            "n_windows":      len(test_df),
            "stages_present": sorted(y_test.unique()),
            "report":         report,
        })

        # 피처 중요도 누적 (7번의 평균을 내기 위해)
        all_importances.append(rf.feature_importances_)

        stages_str = "/".join(STAGE_NAME.get(s, str(s))
                              for s in sorted(y_test.unique()))
        print(f"  [{i}/{len(subjects)}] {test_subject}  "
              f"정확도: {acc:.1%}  창: {len(test_df)}  단계: {stages_str}")

    accs = [r["accuracy"] for r in results]
    mean_acc = np.mean(accs)
    std_acc  = np.std(accs)
    mean_importance = np.mean(all_importances, axis=0)

    print(f"\n  → 평균 정확도: {mean_acc:.1%}  (±{std_acc:.1%})")

    return {
        "label":            label,
        "results":          results,
        "mean_acc":         mean_acc,
        "std_acc":          std_acc,
        "accs":             accs,
        "subjects":         subjects,
        "features":         features,
        "mean_importance":  mean_importance,
    }


# ── 1. 데이터 읽기 ────────────────────────────────────────────
df = pd.read_csv("prepared_multi_hrv.csv")
df["subject_id"] = df["subject_id"].astype(str)

print("=" * 60)
print("[ HRV 피처 추가 전/후 비교 실험 ]")
print(f"  피험자: {df['subject_id'].nunique()}명,  총 창: {len(df)}개")
print("=" * 60)

# ── 2. 두 가지 LOO-CV 실행 ────────────────────────────────────
exp_base = run_loocv(df, FEATURES_BASE, "실험 A — 기존 4개 피처")
exp_hrv  = run_loocv(df, FEATURES_HRV,  "실험 B — HRV 3개 추가 (7개 피처)")

# ── 3. 정확도 비교 테이블 ─────────────────────────────────────
print("\n" + "=" * 60)
print("[ 피험자별 정확도 비교 (A vs B) ]")
print("=" * 60)
print(f"  {'subject':>10}  {'기존 4개':>8}  {'HRV 추가':>8}  {'차이':>6}  판정")
print(f"  {'─'*10}  {'─'*8}  {'─'*8}  {'─'*6}  {'─'*10}")

for r_base, r_hrv in zip(exp_base["results"], exp_hrv["results"]):
    diff = r_hrv["accuracy"] - r_base["accuracy"]
    if diff > 0.01:
        verdict = "↑ 개선"
    elif diff < -0.01:
        verdict = "↓ 하락"
    else:
        verdict = "≈ 동일"
    print(f"  {r_base['subject_id']:>10}  {r_base['accuracy']:>8.1%}  "
          f"{r_hrv['accuracy']:>8.1%}  {diff:>+6.1%}  {verdict}")

# 전체 요약
diff_mean = exp_hrv["mean_acc"] - exp_base["mean_acc"]
print(f"\n  {'평균':>10}  {exp_base['mean_acc']:>8.1%}  "
      f"{exp_hrv['mean_acc']:>8.1%}  {diff_mean:>+6.1%}  "
      f"{'↑ 개선' if diff_mean > 0.005 else '≈ 동일' if abs(diff_mean) <= 0.005 else '↓ 하락'}")

# ── 4. 수면 단계별 F1 비교 ────────────────────────────────────
print("\n" + "=" * 60)
print("[ 수면 단계별 평균 F1-score 비교 ]")
print("  (어떤 단계에서 HRV가 도움이 됐는가)")
print("=" * 60)

all_stages = sorted({s
                     for r in exp_base["results"]
                     for s in r["stages_present"]})

print(f"  {'단계':^12}  {'기존 4개':>8}  {'HRV 추가':>8}  {'차이':>6}")
print(f"  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*6}")

for s in all_stages:
    s_str = str(s)
    name  = STAGE_NAME.get(s, f"stage{s}")

    f1_base_vals = [r["report"][s_str]["f1-score"]
                    for r in exp_base["results"] if s_str in r["report"]]
    f1_hrv_vals  = [r["report"][s_str]["f1-score"]
                    for r in exp_hrv["results"]  if s_str in r["report"]]

    if not f1_base_vals or not f1_hrv_vals:
        continue

    f1_base = np.mean(f1_base_vals)
    f1_hrv  = np.mean(f1_hrv_vals)
    diff    = f1_hrv - f1_base
    mark    = "↑" if diff > 0.02 else ("↓" if diff < -0.02 else "≈")
    print(f"  {name:^12}  {f1_base:>8.3f}  {f1_hrv:>8.3f}  {diff:>+6.3f}  {mark}")

# ── 5. 피처 중요도 ────────────────────────────────────────────
print("\n" + "=" * 60)
print("[ 피처 중요도 — HRV 추가 모델 (7개 피처) ]")
print("  (RandomForest가 어떤 피처를 가장 많이 활용했는가)")
print("=" * 60)

importance_pairs = sorted(
    zip(exp_hrv["features"], exp_hrv["mean_importance"]),
    key=lambda x: x[1],
    reverse=True,
)

for feat, imp in importance_pairs:
    bar   = "█" * int(imp * 50)
    tag   = " ← HRV" if feat.startswith("hrv_") else ""
    print(f"  {feat:15s}  {imp:.4f}  {bar}{tag}")

# ── 6. 최종 결론 ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("[ 최종 결론 ]")
print("=" * 60)

print(f"""
  실험 A (기존 4개 피처):  LOO-CV 평균 {exp_base['mean_acc']:.1%}
  실험 B (HRV 3개 추가):  LOO-CV 평균 {exp_hrv['mean_acc']:.1%}
  변화량:  {diff_mean:+.1%}
""")

if diff_mean > 0.02:
    print("  → HRV 피처가 유의미하게 도움이 됐습니다.")
    print("  → 다음 단계: 더 많은 HRV 지표 (LF/HF ratio 등) 추가 또는")
    print("    온도·SpO2 피처 추가를 고려해볼 수 있습니다.")
elif diff_mean > 0:
    print("  → HRV 피처가 소폭 도움이 됐습니다.")
    print("  → 이 수준의 웨어러블(5초 간격 BPM)에서 HRV 근사값의 한계일 수 있습니다.")
    print("  → 실제 beat-to-beat 데이터(ECG)가 있다면 효과가 더 클 것입니다.")
else:
    print("  → 이 데이터에서는 HRV가 추가 정보를 많이 주지 못했습니다.")
    print("  → 원인: 5초 간격 샘플링 → 임상 HRV와 다른 신호를 측정하게 됨.")
    print("  → 피처 자체보다 모델 구조(LSTM, 윈도우 길이 등)를 바꾸는 게")
    print("    더 효과적일 수 있습니다.")

print(f"""
  학계 벤치마크 (5단계 분류, 웨어러블):  약 57~68%
  현재 모델:  {exp_hrv['mean_acc']:.1%}
""")

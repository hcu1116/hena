# 06_realdata — PhysioNet 실측 데이터 분석

이 디렉토리는 PhysioNet에서 제공하는 공개 수면 데이터셋을 이용한
실측 데이터 분석 및 머신러닝 학습 코드를 담고 있습니다.

---

## 데이터 출처

**데이터셋:**
Motion and heart rate from a wrist-worn wearable and labeled sleep
from polysomnography (sleep-accel)

**URL:** https://physionet.org/content/sleep-accel/

**관련 논문:**
Walch, O., Huang, Y., Forger, D., & Goldstein, C. (2019).
Sleep stage prediction with raw acceleration and
photoplethysmography-derived heart rate from a wrist-worn wearable.
*SLEEP*, 42(12).

**PhysioNet 표준 인용:**
Goldberger, A., Amaral, L., Glass, L., Hausdorff, J., Ivanov, P. C.,
Mark, R., ... & Stanley, H. E. (2000). PhysioBank, PhysioToolkit,
and PhysioNet: Components of a new research resource for complex
physiologic signals. *Circulation*, 101(23), e215–e220.

**분석 코드 참고:** https://github.com/ojwalch/sleep_classifiers

---

## 이 저장소에 원본 데이터가 없는 이유

PhysioNet 원본 데이터는 라이선스 정책에 따라 이 저장소에 포함하지 않습니다.
위 PhysioNet 페이지에서 직접 내려받아 `learning/06_realdata/data/` 에 넣으면
아래 코드를 재현할 수 있습니다.

---

## 데이터 다운로드 방법

사용한 피험자 ID 7명: `1066528`, `1455390`, `2598705`, `2638030`,
`3509524`, `4314139`, `5498603`

각 피험자마다 3종류의 파일이 있습니다.

```bash
# 예시: 피험자 4314139
wget https://physionet.org/files/sleep-accel/1.0.0/heart_rate/4314139_heartrate.txt \
     -O learning/06_realdata/data/4314139_heartrate.txt

wget https://physionet.org/files/sleep-accel/1.0.0/labels/4314139_labeled_sleep.txt \
     -O learning/06_realdata/data/4314139_labeled_sleep.txt

wget https://physionet.org/files/sleep-accel/1.0.0/motion/4314139_acceleration.txt \
     -O learning/06_realdata/data/4314139_acceleration.txt
```

나머지 6명도 동일한 패턴으로 다운로드하면 됩니다.

---

## 코드 파일 구성

| 파일 | 설명 | 필요 데이터 |
|---|---|---|
| `explore.py` | 단일 피험자 데이터 탐색 | raw data |
| `plot_hr.py` | 심박수 시계열 시각화 | raw data |
| `prepare_data.py` | 단일 피험자 전처리 → `prepared.csv` | raw data |
| `prepare_multi.py` | 7명 전처리 → `prepared_multi.csv` | raw data |
| `prepare_multi_hrv.py` | HRV 피처 추가 전처리 → `prepared_multi_hrv.csv` | raw data |
| `train_model.py` | 단일 피험자 RandomForest 학습 | `prepared.csv` |
| `train_multi.py` | 7명 통합 모델 학습 | `prepared_multi.csv` |
| `cross_validation.py` | Leave-One-Subject-Out 교차검증 | `prepared_multi.csv` |
| `cross_validation_hrv.py` | HRV 피처 포함 교차검증 | `prepared_multi_hrv.csv` |

> `train_*` / `cross_validation_*` 파일은 전처리된 CSV만 필요하므로
> raw data 없이도 실행 가능합니다 (CSV는 저장소에 포함되어 있음).

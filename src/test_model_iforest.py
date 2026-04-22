import pandas as pd
from pathlib import Path

from model_iforest import train_and_score_isolation_forest, FEATURE_COLS

features = pd.read_csv("data/processed/features_user_day_demo.csv")

model, scaler, scored = train_and_score_isolation_forest(
    features,
    contamination=0.05  # 5% flagged as anomalies
)

print("Scored head:")
print(scored[["user", "day", "anomaly_score", "is_anomaly"] + FEATURE_COLS].head())

print("\nTop 10 most anomalous user-days:")
top10 = scored.sort_values("anomaly_score", ascending=False).head(10)
print(top10[["user", "day", "anomaly_score", "is_anomaly"] + FEATURE_COLS])

Path("data/processed").mkdir(parents=True, exist_ok=True)
scored.to_csv("data/processed/scored_user_day_demo.csv", index=False)
print("\nSaved: data/processed/scored_user_day_demo.csv")
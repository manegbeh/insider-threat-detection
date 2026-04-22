import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parent))

import pandas as pd
from risk import apply_risk_scoring, FEATURE_COLS

scored = pd.read_csv("data/processed/scored_user_day_demo.csv")

alerts = apply_risk_scoring(scored)

print("Alerts head:")
print(alerts[["user", "day", "anomaly_score", "risk_band", "top_reason"] + FEATURE_COLS].head())

print("\nRisk band counts:")
print(alerts["risk_band"].value_counts())

print("\nHigh risk examples:")
high = alerts[alerts["risk_band"] == "High"].sort_values("anomaly_score", ascending=False).head(10)
print(high[["user", "day", "anomaly_score", "risk_band", "top_reason"] + FEATURE_COLS])

_Path("data/processed").mkdir(parents=True, exist_ok=True)
alerts.to_csv("data/processed/alerts_user_day_demo.csv", index=False)
print("\nSaved: data/processed/alerts_user_day_demo.csv")
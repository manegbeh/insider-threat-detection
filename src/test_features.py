from pathlib import Path
import pandas as pd

from pipeline_load import PipelineConfig
from features import build_user_day_features

cfg = PipelineConfig(data_dir=Path("data/raw"), demo_mode=True)

events = pd.read_csv("data/processed/events_demo.csv")
features = build_user_day_features(events, cfg)

print(features.head())
print("\nRows:", len(features))
print("\nFeature summary:")
print(features.describe())

Path("data/processed").mkdir(parents=True, exist_ok=True)
features.to_csv("data/processed/features_user_day_demo.csv", index=False)
print("\nSaved: data/processed/features_user_day_demo.csv")
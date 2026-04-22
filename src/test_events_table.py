from pathlib import Path
from pipeline_load import PipelineConfig, load_all_events

cfg = PipelineConfig(
    data_dir=Path("data/raw"),
    demo_mode=True
)

events = load_all_events(cfg)

print(events.head())
print("\nEvent counts:")
print(events["event_type"].value_counts())

print("\nDate range:")
print(events["timestamp"].min(), "->", events["timestamp"].max())

print("\nUnique users:", events["user"].nunique())

# Save for reuse
Path("data/processed").mkdir(parents=True, exist_ok=True)
events.to_csv("data/processed/events_demo.csv", index=False)
print("\nSaved: data/processed/events_demo.csv")
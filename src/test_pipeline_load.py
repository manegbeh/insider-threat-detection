from pathlib import Path
from pipeline_load import PipelineConfig, load_log

cfg = PipelineConfig(
    data_dir=Path("data/raw"),
    demo_mode=True
)

logon = load_log(
    cfg.data_dir / "logon.csv",
    event_type="logon",
    cfg=cfg,
    usecols=["date", "user", "pc", "activity"]
)

print(logon.head())
print(logon["event_type"].value_counts())
print(f"Users in demo window: {logon['user'].nunique()}")
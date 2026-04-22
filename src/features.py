from __future__ import annotations

import pandas as pd
from pathlib import Path
from pipeline_load import PipelineConfig, is_after_hours


def build_user_day_features(events: pd.DataFrame, cfg: PipelineConfig) -> pd.DataFrame:
    # After-hours flag for every event
    events = events.copy()
    events["after_hours"] = events["hour"].apply(lambda h: is_after_hours(int(h), cfg))

    # Basic counts by event type
    base = (
        events.groupby(["user", "day", "event_type"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )

    # Rename event type columns into your required feature names
    base = base.rename(
        columns={
            "logon": "logons_per_day",
            "http": "website_visits_count",
            "file": "file_access_count",
            "device": "removable_media_usage_count",
            "email": "emails_sent_count",
        }
    )

    # After-hours count (across all events or just logons; MVP choice: all events)
    after_hours = (
        events[events["after_hours"]]
        .groupby(["user", "day"])
        .size()
        .reset_index(name="after_hours_activity_count")
    )

    # Merge after-hours into base feature table
    features = base.merge(after_hours, on=["user", "day"], how="left")
    features["after_hours_activity_count"] = features["after_hours_activity_count"].fillna(0).astype(int)

    # Ensure all required feature columns exist even if a type is missing
    required = [
        "logons_per_day",
        "after_hours_activity_count",
        "file_access_count",
        "removable_media_usage_count",
        "emails_sent_count",
        "website_visits_count",
    ]
    for col in required:
        if col not in features.columns:
            features[col] = 0

    # Clean ordering
    features = features[["user", "day"] + required].sort_values(["day", "user"]).reset_index(drop=True)
    return features


def load_events_processed(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"])
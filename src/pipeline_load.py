from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pandas as pd


def _safe_read_csv(csv_path: Path, usecols: list[str] | None) -> pd.DataFrame:
    if usecols is None:
        df = pd.read_csv(csv_path, on_bad_lines='skip')
    else:
        header_cols = set(pd.read_csv(csv_path, nrows=0).columns)
        wanted = [c for c in usecols if c in header_cols]

        if "user" not in header_cols:
            raise ValueError(f"'user' column not found in {csv_path.name}.")
        if ("date" not in header_cols) and ("timestamp" not in header_cols):
            raise ValueError(f"No datetime column found in {csv_path.name}.")

        if "user" not in wanted:
            wanted.append("user")
        if "date" in header_cols and "date" not in wanted:
            wanted.append("date")
        if "timestamp" in header_cols and "timestamp" not in wanted:
            wanted.append("timestamp")

        df = pd.read_csv(csv_path, usecols=wanted, on_bad_lines='skip')

    return df


@dataclass
class PipelineConfig:
    data_dir: Path
    demo_mode: bool = True
    date_start: str = "2010-01-01"  
    date_end: str = "2010-02-28"   
    user_sample_size: int | None = 100
    after_hours_start: int = 18
    after_hours_end: int = 8


def _parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        dt_col = "date"
    elif "timestamp" in df.columns:
        dt_col = "timestamp"
    else:
        raise ValueError(f"No datetime column found. Columns: {list(df.columns)}")

    df["timestamp"] = pd.to_datetime(df[dt_col], errors="coerce", infer_datetime_format=True, cache=True)
    df = df.dropna(subset=["timestamp"])
    df["day"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    return df


def _normalise_user(df: pd.DataFrame) -> pd.DataFrame:
    if "user" not in df.columns:
        raise ValueError(f"'user' column not found. Columns: {list(df.columns)}")
    df["user"] = df["user"].astype(str).str.strip()
    return df


def _filter_demo(df: pd.DataFrame, cfg: PipelineConfig) -> pd.DataFrame:
    if not cfg.demo_mode:
        return df

    start = pd.to_datetime(cfg.date_start)
    end = pd.to_datetime(cfg.date_end)

    df = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)]

    if cfg.user_sample_size is not None:
        users = sorted(df["user"].dropna().unique().tolist())
        users = users[: cfg.user_sample_size]
        df = df[df["user"].isin(users)]

    return df


def load_log(csv_path: Path, event_type: str, cfg: PipelineConfig, usecols: list[str] | None = None) -> pd.DataFrame:
    df = _safe_read_csv(csv_path, usecols=usecols)
    df = _normalise_user(df)
    df = _parse_datetime(df)

    # Normalise common optional fields
    if "pc" not in df.columns:
        df["pc"] = None
    if "activity" not in df.columns:
        df["activity"] = None

    df["event_type"] = event_type
    # Derive a human-readable action field when an activity column exists
    if "activity" in df.columns:
        df["action"] = df["activity"].astype(str).str.strip()
        df["action"] = df["action"].where(df["action"] != "nan", None)
    else:
        df["action"] = None

    df = _filter_demo(df, cfg)

    # Keep only canonical columns for the MVP
    keep = ["user", "timestamp", "day", "hour", "pc", "event_type", "action"]
    return df[keep]

def load_all_events(cfg: PipelineConfig) -> pd.DataFrame:
    raw = cfg.data_dir

    logon = load_log(
        raw / "logon.csv",
        event_type="logon",
        cfg=cfg,
        usecols=["date", "user", "pc", "activity"],
    )

    device = load_log(
        raw / "device.csv",
        event_type="device",
        cfg=cfg,
        usecols=["date", "user", "pc", "activity"],
    )

    http = load_log(
        raw / "http.csv",
        event_type="http",
        cfg=cfg,
        usecols=["date", "user", "pc", "url"],
    )
    # Put url into action so we keep something meaningful
    if "url" in http.columns:
        http["action"] = http["action"].fillna(http["url"])

    file_df = load_log(
        raw / "file.csv",
        event_type="file",
        cfg=cfg,
        usecols=["date", "user", "pc", "filename"],
    )
    if "filename" in file_df.columns:
        file_df["action"] = file_df["action"].fillna(file_df["filename"])

    email = load_log(
        raw / "email.csv",
        event_type="email",
        cfg=cfg,
        usecols=["date", "user", "pc", "activity"],
    )

    events = pd.concat([logon, device, http, file_df, email], ignore_index=True)
    events = events.sort_values(["timestamp", "user"]).reset_index(drop=True)
    return events

def is_after_hours(hour: int, cfg: PipelineConfig) -> bool:
    return (hour >= cfg.after_hours_start) or (hour < cfg.after_hours_end)
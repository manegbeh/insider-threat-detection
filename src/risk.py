from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLS = [
    "logons_per_day",
    "after_hours_activity_count",
    "file_access_count",
    "removable_media_usage_count",
    "emails_sent_count",
    "website_visits_count",
]

REASON_LABELS = {
    "after_hours_activity_count": "After-hours spike",
    "removable_media_usage_count": "Unusual removable media activity",
    "file_access_count": "File access surge",
    "emails_sent_count": "Email volume spike",
    "website_visits_count": "Web activity spike",
    "logons_per_day": "Logon spike",
}


def add_risk_bands(df: pd.DataFrame, high_pct: float = 0.95, med_pct: float = 0.85) -> pd.DataFrame:
    """
    Convert anomaly_score into Low/Medium/High via percentiles.
    Default: High = top 5%, Medium = next 10%, Low = rest.
    """
    out = df.copy()

    high_thr = out["anomaly_score"].quantile(high_pct)
    med_thr = out["anomaly_score"].quantile(med_pct)

    out["risk_band"] = np.where(
        out["anomaly_score"] >= high_thr, "High",
        np.where(out["anomaly_score"] >= med_thr, "Medium", "Low")
    )
    return out


def add_top_reason(df: pd.DataFrame, window_days: int = 14) -> pd.DataFrame:
    """
    Adds a top_reason tag by finding which feature spiked most vs the user's recent baseline.

    Baseline approach:
    - For each user, compute rolling mean and rolling std over the previous N days.
    - Compute z-score = (today - rolling_mean) / rolling_std
    - Top reason = feature with highest z-score (largest spike)
    """
    out = df.copy()
    out["day"] = pd.to_datetime(out["day"])

    out = out.sort_values(["user", "day"]).reset_index(drop=True)

    top_reasons: list[str] = []

    # Compute rolling stats per user
    for _, user_df in out.groupby("user", sort=False):
        user_df = user_df.copy()

        # Rolling mean/std of previous days only (shift by 1 so we do not "peek" at today)
        rolling_mean = user_df[FEATURE_COLS].rolling(window=window_days, min_periods=3).mean().shift(1)
        rolling_std = user_df[FEATURE_COLS].rolling(window=window_days, min_periods=3).std(ddof=0).shift(1)

        # Avoid divide by zero by replacing 0 std with NaN
        rolling_std = rolling_std.replace(0, np.nan)

        z = (user_df[FEATURE_COLS] - rolling_mean) / rolling_std

        # If we do not have enough history, z will be NaN. Treat as no clear spike.
        z = z.fillna(-np.inf)

        # Choose feature with max z-score row-wise
        best_feature = z.idxmax(axis=1)

        # Map to human labels
        for f in best_feature:
            top_reasons.append(REASON_LABELS.get(f, "Unusual activity"))

    out["top_reason"] = top_reasons

    # If risk is Low, you can optionally set reason to something softer
    out.loc[out["risk_band"] == "Low", "top_reason"] = "Normal range"

    return out


def apply_risk_scoring(scored_df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience wrapper: bands first, then top reason.
    """
    out = add_risk_bands(scored_df, high_pct=0.95, med_pct=0.85)
    out = add_top_reason(out, window_days=14)
    return out
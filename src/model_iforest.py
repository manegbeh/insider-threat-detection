from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURE_COLS = [
    "logons_per_day",
    "after_hours_activity_count",
    "file_access_count",
    "removable_media_usage_count",
    "emails_sent_count",
    "website_visits_count",
]


def train_and_score_isolation_forest(
    features_df: pd.DataFrame,
    contamination: float = 0.05,
    random_state: int = 42,
):
    """
    Trains Isolation Forest and returns:
    - model
    - scaler
    - dataframe with anomaly_score and is_anomaly

    Notes:
    - We scale features to give each feature a comparable range.
    - We convert sklearn's output so that higher = more anomalous (more intuitive for risk).
    """
    df = features_df.copy()

    X = df[FEATURE_COLS].fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    # decision_function: higher means more "normal"
    normality = model.decision_function(X_scaled)

    # Convert to anomaly score where higher means more anomalous
    df["anomaly_score"] = -normality

    # model.predict: -1 anomaly, +1 normal
    df["is_anomaly"] = (model.predict(X_scaled) == -1).astype(int)

    return model, scaler, df
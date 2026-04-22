import pandas as pd
import streamlit as st

FEATURE_COLS = [
    "logons_per_day",
    "after_hours_activity_count",
    "file_access_count",
    "removable_media_usage_count",
    "emails_sent_count",
    "website_visits_count",
]

RISK_ICON = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}

st.set_page_config(page_title="Insider Threat Dashboard", layout="wide")

# Lightweight CSS polish (kept minimal so it runs on assessor machines)
st.markdown(
    """
    <style>
      /* Global font size reduction */
      html, body, [class*="css"] {
        font-size: 13px;
      }

      .card {
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 14px;
        padding: 12px 14px; /* slightly tighter */
        background: rgba(255,255,255,0.03);
      }

      .small-muted {
        color: rgba(255,255,255,0.65);
        font-size: 0.85rem;
      }

      /* Badge styling */
      .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        border: 1px solid rgba(255,255,255,0.12);
        background: rgba(255,255,255,0.04);
      }

      .badge-high { border-color: rgba(255, 80, 80, 0.35); }
      .badge-med  { border-color: rgba(255, 180, 60, 0.35); }
      .badge-low  { border-color: rgba(80, 220, 140, 0.35); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_alerts() -> pd.DataFrame:
    df = pd.read_csv("data/processed/alerts_user_day_demo.csv")
    df["day"] = pd.to_datetime(df["day"])
    return df


alerts = load_alerts()

# -------------------------
# Sidebar (filters only)
# -------------------------
st.sidebar.header("Filters")

min_day = alerts["day"].min().date()
max_day = alerts["day"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_day, max_day),
    min_value=min_day,
    max_value=max_day,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_day, max_day

risk_levels = st.sidebar.multiselect(
    "Risk level",
    options=["Low", "Medium", "High"],
    default=["High", "Medium", "Low"],
)

user_options = ["All"] + sorted(alerts["user"].unique().tolist())
selected_user = st.sidebar.selectbox("User", options=user_options, index=0)

st.sidebar.caption("Tip: Filter alerts, then select one alert to investigate.")

# Apply filters
filtered = alerts[(alerts["day"].dt.date >= start_date) & (alerts["day"].dt.date <= end_date)]
filtered = filtered[filtered["risk_band"].isin(risk_levels)]

if selected_user != "All":
    filtered = filtered[filtered["user"] == selected_user]

filtered = filtered.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

# Add risk icon column for the table
filtered = filtered.copy()
filtered["risk"] = filtered["risk_band"].map(RISK_ICON).fillna("")

# -------------------------
# Header + KPI row
# -------------------------
st.title("Insider Threat Alerts Dashboard")

# Put context directly under the title to avoid an empty header column
st.caption("MVP: CERT logs → features → Isolation Forest → risk bands + reasons")

ctx1, ctx2 = st.columns([1, 1], gap="small")
with ctx1:
    st.markdown(f"**Window:** {start_date} to {end_date}")
with ctx2:
    st.markdown(f"**Alerts shown:** {len(filtered)}")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total", f"{len(filtered)}")
k2.metric("High", f"{(filtered['risk_band'] == 'High').sum()}")
k3.metric("Medium", f"{(filtered['risk_band'] == 'Medium').sum()}")
k4.metric("Low", f"{(filtered['risk_band'] == 'Low').sum()}")
k5.metric("Users", f"{filtered['user'].nunique()}")

st.divider()

# -------------------------
# Two-panel layout
# -------------------------
left, right = st.columns([1.2, 1.0], gap="large")

with left:
    st.subheader("Alerts queue")
    st.caption("Sorted by anomaly score (highest first).")

    # Display a compact, analyst-friendly case queue (like your wireframe)
    queue = filtered.copy()
    queue["Date"] = queue["day"].dt.strftime("%Y-%m-%d")
    queue["Risk"] = queue["risk"] + " " + queue["risk_band"]
    queue["User"] = queue["user"]
    queue["Score"] = queue["anomaly_score"].round(3)
    queue["Top reason"] = queue["top_reason"]

    queue_cols = ["Date", "Risk", "User", "Score", "Top reason"]
    st.dataframe(queue[queue_cols], use_container_width=True, height=520)

with right:
    st.subheader("Investigation panel")

    if len(filtered) == 0:
        st.info("No alerts match the current filters.")
    else:
        # ID string for selecting an alert
        filtered["alert_id"] = (
            filtered["day"].dt.strftime("%Y-%m-%d")
            + " | "
            + filtered["user"]
            + " | "
            + filtered["risk_band"]
            + " | score="
            + filtered["anomaly_score"].round(3).astype(str)
        )

        selected_id = st.selectbox("Select an alert", options=filtered["alert_id"].tolist(), index=0)
        row = filtered[filtered["alert_id"] == selected_id].iloc[0]

        # Top details in a clean card
        st.markdown('<div class="card">', unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        d1.metric("Risk", f"{RISK_ICON.get(row['risk_band'], '')} {row['risk_band']}")
        d2.metric("Score", f"{float(row['anomaly_score']):.4f}")
        d3.metric("Top reason", f"{row['top_reason']}")
        st.markdown(
            f"<div class='small-muted'>User: <b>{row['user']}</b> · Day: <b>{row['day'].date()}</b></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        tabs = st.tabs(["Feature snapshot", "Baseline comparison", "User timeline"])

        with tabs[0]:
            st.markdown("**Feature values (selected day)**")

            feature_table = pd.DataFrame({
                "Feature": [
                    "Logons per day",
                    "After-hours activity count",
                    "File access count",
                    "Removable media usage count",
                    "Emails sent count",
                    "Website visits count",
                ],
                "Value": [
                    int(row["logons_per_day"]),
                    int(row["after_hours_activity_count"]),
                    int(row["file_access_count"]),
                    int(row["removable_media_usage_count"]),
                    int(row["emails_sent_count"]),
                    int(row["website_visits_count"]),
                ],
            })

            st.dataframe(feature_table, use_container_width=True, hide_index=True)

        with tabs[1]:
            st.markdown("**Feature breakdown vs user baseline**")
            user_hist = alerts[(alerts["user"] == row["user"]) & (alerts["day"] != row["day"])]

            if len(user_hist) < 3:
                st.info("Not enough history for a baseline comparison.")
            else:
                baseline = user_hist[FEATURE_COLS].mean()

                compare = pd.DataFrame({
                    "Feature": [
                        "Logons per day",
                        "After-hours activity count",
                        "File access count",
                        "Removable media usage count",
                        "Emails sent count",
                        "Website visits count",
                    ],
                    "Today": [
                        float(row["logons_per_day"]),
                        float(row["after_hours_activity_count"]),
                        float(row["file_access_count"]),
                        float(row["removable_media_usage_count"]),
                        float(row["emails_sent_count"]),
                        float(row["website_visits_count"]),
                    ],
                    "Baseline avg": [
                        float(baseline["logons_per_day"]),
                        float(baseline["after_hours_activity_count"]),
                        float(baseline["file_access_count"]),
                        float(baseline["removable_media_usage_count"]),
                        float(baseline["emails_sent_count"]),
                        float(baseline["website_visits_count"]),
                    ],
                })
                compare["Diff"] = (compare["Today"] - compare["Baseline avg"]).round(2)
                compare["Today"] = compare["Today"].round(2)
                compare["Baseline avg"] = compare["Baseline avg"].round(2)

                st.dataframe(compare, use_container_width=True, hide_index=True)
                st.bar_chart(compare.set_index("Feature")[["Today", "Baseline avg"]])

        with tabs[2]:
            st.markdown("**Anomaly score over time (selected user)**")
            st.caption("Use this to see whether the alert is a one-off spike or part of a repeated pattern.")

            user_scores = alerts[alerts["user"] == row["user"]].sort_values("day")[["day", "anomaly_score"]].copy()
            user_scores = user_scores.set_index("day")

            # Marker series for selected day (NaN elsewhere)
            user_scores["selected_day"] = float("nan")
            user_scores.loc[pd.to_datetime(row["day"]), "selected_day"] = float(row["anomaly_score"])

            # One chart with both lines
            st.line_chart(user_scores.rename(columns={"anomaly_score": "score"})[["score", "selected_day"]])
import pandas as pd
import streamlit as st
import altair as alt

FEATURE_COLS = [
    "logons_per_day",
    "after_hours_activity_count",
    "file_access_count",
    "removable_media_usage_count",
    "emails_sent_count",
    "website_visits_count",
]

FEATURE_LABELS = {
    "logons_per_day": "Logons per day",
    "after_hours_activity_count": "After-hours activity",
    "file_access_count": "File access count",
    "removable_media_usage_count": "Removable media usage",
    "emails_sent_count": "Emails sent",
    "website_visits_count": "Website visits",
}

RISK_COLOUR = {"High": "#FF4B4B", "Medium": "#FFA500", "Low": "#21C55D"}
RISK_ICON   = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}

st.set_page_config(
    page_title="Insider Threat Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

/* ── Page background ── */
.stApp {
    background: #0D1117;
}

/* ── KPI cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 24px;
}
.kpi-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px 20px;
}
.kpi-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8B949E;
    font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 600;
    color: #E6EDF3;
    font-family: 'IBM Plex Mono', monospace;
}
.kpi-value.high  { color: #FF4B4B; }
.kpi-value.med   { color: #FFA500; }
.kpi-value.low   { color: #21C55D; }

/* ── Section headers ── */
.section-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8B949E;
    font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262D;
}

/* ── Investigation card ── */
.inv-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
}
.inv-user {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #8B949E;
    margin-top: 10px;
}
.risk-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.05em;
}
.risk-high { background: rgba(255,75,75,0.15); color: #FF4B4B; border: 1px solid rgba(255,75,75,0.3); }
.risk-med  { background: rgba(255,165,0,0.15);  color: #FFA500; border: 1px solid rgba(255,165,0,0.3); }
.risk-low  { background: rgba(33,197,93,0.15);  color: #21C55D; border: 1px solid rgba(33,197,93,0.3); }

/* ── Diff pill ── */
.diff-pos { color: #FF4B4B; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }
.diff-neg { color: #21C55D; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }

/* ── Streamlit overrides ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }
div[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; }
.stTabs [data-baseweb="tab"] {
    font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.stSidebar { background: #0D1117; border-right: 1px solid #21262D; }
h1 { font-family: 'IBM Plex Sans', sans-serif !important; font-weight: 300 !important; letter-spacing: -0.01em; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data
def load_alerts() -> pd.DataFrame:
    df = pd.read_csv("data/processed/alerts_user_day_demo.csv")
    df["day"] = pd.to_datetime(df["day"])
    return df

alerts = load_alerts()


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### 🛡️ Insider Threat")
    st.markdown("<div style='color:#8B949E;font-size:12px;margin-bottom:24px;'>CERT v4.2 · Isolation Forest</div>", unsafe_allow_html=True)

    st.markdown("**Date range**")
    min_day = alerts["day"].min().date()
    max_day = alerts["day"].max().date()
    date_range = st.date_input("", value=(min_day, max_day), min_value=min_day, max_value=max_day, label_visibility="collapsed")

    st.markdown("**Risk level**")
    risk_levels = st.multiselect("", options=["High", "Medium", "Low"], default=["High", "Medium", "Low"], label_visibility="collapsed")

    st.markdown("**User**")
    user_options = ["All"] + sorted(alerts["user"].unique().tolist())
    selected_user = st.selectbox("", options=user_options, index=0, label_visibility="collapsed")

    st.divider()
    st.markdown("<div style='color:#8B949E;font-size:11px;'>Select filters above, then click an alert in the queue to investigate.</div>", unsafe_allow_html=True)


# ── Apply filters ─────────────────────────────────────────────────────────────

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_day, max_day

filtered = alerts[
    (alerts["day"].dt.date >= start_date) &
    (alerts["day"].dt.date <= end_date) &
    (alerts["risk_band"].isin(risk_levels))
]
if selected_user != "All":
    filtered = filtered[filtered["user"] == selected_user]

filtered = filtered.sort_values("anomaly_score", ascending=False).reset_index(drop=True)


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("# Insider Threat Alerts Dashboard")
st.markdown(f"<div style='color:#8B949E;font-size:13px;margin-bottom:24px;'>Window: {start_date} → {end_date} &nbsp;·&nbsp; {len(filtered)} alerts &nbsp;·&nbsp; {filtered['user'].nunique()} users</div>", unsafe_allow_html=True)


# ── KPI row ───────────────────────────────────────────────────────────────────

n_high = int((filtered["risk_band"] == "High").sum())
n_med  = int((filtered["risk_band"] == "Medium").sum())
n_low  = int((filtered["risk_band"] == "Low").sum())

st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Total alerts</div>
    <div class="kpi-value">{len(filtered)}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">High risk</div>
    <div class="kpi-value high">{n_high}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Medium risk</div>
    <div class="kpi-value med">{n_med}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Low risk</div>
    <div class="kpi-value low">{n_low}</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Unique users</div>
    <div class="kpi-value">{filtered["user"].nunique()}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Risk distribution bar chart ───────────────────────────────────────────────

risk_dist = (
    filtered["risk_band"]
    .value_counts()
    .reindex(["High", "Medium", "Low"], fill_value=0)
    .reset_index()
)
risk_dist.columns = ["Risk", "Count"]
risk_dist["Colour"] = risk_dist["Risk"].map(RISK_COLOUR)

dist_chart = (
    alt.Chart(risk_dist)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
    .encode(
        x=alt.X("Risk:N", sort=["High", "Medium", "Low"], axis=alt.Axis(labelColor="#8B949E", tickColor="#21262D", domainColor="#21262D", labelFont="IBM Plex Mono", titleColor="#8B949E")),
        y=alt.Y("Count:Q", axis=alt.Axis(labelColor="#8B949E", gridColor="#21262D", domainColor="#21262D", tickColor="#21262D", labelFont="IBM Plex Mono", titleColor="#8B949E")),
        color=alt.Color("Colour:N", scale=None),
        tooltip=["Risk", "Count"],
    )
    .properties(height=120, background="#161B22", padding={"left": 16, "right": 16, "top": 12, "bottom": 8})
    .configure_view(stroke=None)
)

st.altair_chart(dist_chart, use_container_width=True)

st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)


# ── Two-panel layout ──────────────────────────────────────────────────────────

left, right = st.columns([1.15, 1.0], gap="large")


# ── LEFT: Alerts queue ────────────────────────────────────────────────────────

with left:
    st.markdown('<div class="section-title">Alerts queue</div>', unsafe_allow_html=True)

    if len(filtered) == 0:
        st.info("No alerts match the current filters.")
    else:
        queue = filtered.copy()
        queue["Date"]       = queue["day"].dt.strftime("%Y-%m-%d")
        queue["Risk"]       = queue["risk_band"].map(RISK_ICON) + "  " + queue["risk_band"]
        queue["User"]       = queue["user"]
        queue["Score"]      = queue["anomaly_score"].round(3)
        queue["Top reason"] = queue["top_reason"]

        st.dataframe(
            queue[["Date", "Risk", "User", "Score", "Top reason"]],
            use_container_width=True,
            height=500,
            hide_index=False,
        )


# ── RIGHT: Investigation panel ────────────────────────────────────────────────

with right:
    st.markdown('<div class="section-title">Investigation panel</div>', unsafe_allow_html=True)

    if len(filtered) == 0:
        st.info("No alerts to investigate.")
    else:
        filtered["alert_id"] = (
            filtered["day"].dt.strftime("%Y-%m-%d") + " | " +
            filtered["user"] + " | " +
            filtered["risk_band"] + " | score=" +
            filtered["anomaly_score"].round(3).astype(str)
        )

        selected_id = st.selectbox("Select an alert", options=filtered["alert_id"].tolist(), index=0, label_visibility="collapsed")
        row = filtered[filtered["alert_id"] == selected_id].iloc[0]
        rb  = row["risk_band"]
        badge_cls = {"High": "risk-high", "Medium": "risk-med", "Low": "risk-low"}.get(rb, "")

        # Investigation card
        st.markdown(f"""
        <div class="inv-card">
            <span class="risk-badge {badge_cls}">{RISK_ICON.get(rb,'')} {rb}</span>
            <div style="display:flex;gap:40px;margin-top:14px;">
                <div>
                    <div class="kpi-label">Anomaly score</div>
                    <div style="font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:#E6EDF3;">{float(row['anomaly_score']):.4f}</div>
                </div>
                <div>
                    <div class="kpi-label">Top reason</div>
                    <div style="font-size:16px;font-weight:500;color:#E6EDF3;margin-top:4px;">{row['top_reason']}</div>
                </div>
            </div>
            <div class="inv-user">User: {row['user']} &nbsp;·&nbsp; Day: {row['day'].date()}</div>
        </div>
        """, unsafe_allow_html=True)

        tabs = st.tabs(["📊  Feature snapshot", "📈  Baseline comparison", "⏱  User timeline"])

        # Tab 1: Feature snapshot as horizontal bar chart
        with tabs[0]:
            feat_vals = pd.DataFrame({
                "Feature": list(FEATURE_LABELS.values()),
                "Value":   [float(row[c]) for c in FEATURE_COLS],
            })

            bar = (
                alt.Chart(feat_vals)
                .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#2F81F7")
                .encode(
                    y=alt.Y("Feature:N", sort="-x", axis=alt.Axis(labelColor="#8B949E", tickColor="#21262D", domainColor="#21262D", labelFont="IBM Plex Mono", labelLimit=200)),
                    x=alt.X("Value:Q", axis=alt.Axis(labelColor="#8B949E", gridColor="#21262D", domainColor="#21262D", tickColor="#21262D", labelFont="IBM Plex Mono")),
                    tooltip=["Feature", "Value"],
                )
                .properties(height=200, background="#0D1117", padding={"left": 8, "right": 16, "top": 8, "bottom": 8})
                .configure_view(stroke=None)
            )
            st.altair_chart(bar, use_container_width=True)

        # Tab 2: Baseline comparison
        with tabs[1]:
            user_hist = alerts[(alerts["user"] == row["user"]) & (alerts["day"] != row["day"])]

            if len(user_hist) < 3:
                st.info("Not enough history for a baseline comparison.")
            else:
                baseline = user_hist[FEATURE_COLS].mean()
                compare = pd.DataFrame({
                    "Feature":      list(FEATURE_LABELS.values()),
                    "Today":        [float(row[c]) for c in FEATURE_COLS],
                    "Baseline avg": [float(baseline[c]) for c in FEATURE_COLS],
                })
                compare["Diff"] = (compare["Today"] - compare["Baseline avg"]).round(2)
                compare["Today"]        = compare["Today"].round(2)
                compare["Baseline avg"] = compare["Baseline avg"].round(2)

                # Grouped bar chart: Today vs Baseline
                melted = compare.melt(id_vars="Feature", value_vars=["Today", "Baseline avg"], var_name="Series", value_name="Value")
                grouped = (
                    alt.Chart(melted)
                    .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
                    .encode(
                        y=alt.Y("Feature:N", sort="-x", axis=alt.Axis(labelColor="#8B949E", tickColor="#21262D", domainColor="#21262D", labelFont="IBM Plex Mono", labelLimit=200)),
                        x=alt.X("Value:Q", axis=alt.Axis(labelColor="#8B949E", gridColor="#21262D", domainColor="#21262D", tickColor="#21262D", labelFont="IBM Plex Mono")),
                        color=alt.Color("Series:N", scale=alt.Scale(domain=["Today", "Baseline avg"], range=["#FF4B4B", "#2F81F7"]),
                                        legend=alt.Legend(labelColor="#8B949E", labelFont="IBM Plex Mono", titleColor="#8B949E")),
                        yOffset="Series:N",
                        tooltip=["Feature", "Series", "Value"],
                    )
                    .properties(height=220, background="#0D1117", padding={"left": 8, "right": 16, "top": 8, "bottom": 8})
                    .configure_view(stroke=None)
                )
                st.altair_chart(grouped, use_container_width=True)

                # Diff table
                def fmt_diff(v):
                    if v > 0:
                        return f"<span class='diff-pos'>+{v}</span>"
                    elif v < 0:
                        return f"<span class='diff-neg'>{v}</span>"
                    return f"<span style='color:#8B949E;font-family:IBM Plex Mono,monospace;font-size:12px;'>{v}</span>"

                rows_html = "".join(
                    f"<tr style='border-bottom:1px solid #21262D'>"
                    f"<td style='padding:8px 12px;color:#E6EDF3;font-size:12px;'>{r['Feature']}</td>"
                    f"<td style='padding:8px 12px;color:#E6EDF3;font-family:IBM Plex Mono,monospace;font-size:12px;text-align:right;'>{r['Today']}</td>"
                    f"<td style='padding:8px 12px;color:#8B949E;font-family:IBM Plex Mono,monospace;font-size:12px;text-align:right;'>{r['Baseline avg']}</td>"
                    f"<td style='padding:8px 12px;text-align:right;'>{fmt_diff(r['Diff'])}</td>"
                    f"</tr>"
                    for _, r in compare.iterrows()
                )
                st.markdown(f"""
                <table style='width:100%;border-collapse:collapse;background:#161B22;border-radius:8px;overflow:hidden;'>
                  <thead>
                    <tr style='background:#21262D;'>
                      <th style='padding:8px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#8B949E;font-family:IBM Plex Mono,monospace;'>Feature</th>
                      <th style='padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#FF4B4B;font-family:IBM Plex Mono,monospace;'>Today</th>
                      <th style='padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#2F81F7;font-family:IBM Plex Mono,monospace;'>Baseline</th>
                      <th style='padding:8px 12px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#8B949E;font-family:IBM Plex Mono,monospace;'>Diff</th>
                    </tr>
                  </thead>
                  <tbody>{rows_html}</tbody>
                </table>
                """, unsafe_allow_html=True)

        # Tab 3: User timeline
        with tabs[2]:
            user_scores = (
                alerts[alerts["user"] == row["user"]]
                .sort_values("day")[["day", "anomaly_score", "risk_band"]]
                .copy()
            )

            # Colour points by risk band
            user_scores["colour"] = user_scores["risk_band"].map(RISK_COLOUR).fillna("#8B949E")

            line = (
                alt.Chart(user_scores)
                .mark_line(color="#2F81F7", strokeWidth=1.5)
                .encode(
                    x=alt.X("day:T", axis=alt.Axis(labelColor="#8B949E", tickColor="#21262D", domainColor="#21262D", format="%b %d", labelFont="IBM Plex Mono")),
                    y=alt.Y("anomaly_score:Q", axis=alt.Axis(labelColor="#8B949E", gridColor="#21262D", domainColor="#21262D", tickColor="#21262D", labelFont="IBM Plex Mono", title="Anomaly score")),
                )
            )
            points = (
                alt.Chart(user_scores)
                .mark_circle(size=50)
                .encode(
                    x="day:T",
                    y="anomaly_score:Q",
                    color=alt.Color("colour:N", scale=None),
                    tooltip=["day:T", "anomaly_score:Q", "risk_band:N"],
                )
            )
            # Highlight selected day
            selected_day_df = user_scores[user_scores["day"] == pd.to_datetime(row["day"])]
            highlight = (
                alt.Chart(selected_day_df)
                .mark_circle(size=120, color="#FFD700")
                .encode(x="day:T", y="anomaly_score:Q", tooltip=["day:T", "anomaly_score:Q"])
            )

            timeline = (
                (line + points + highlight)
                .properties(height=200, background="#0D1117", padding={"left": 8, "right": 16, "top": 8, "bottom": 8})
                .configure_view(stroke=None)
                .configure_axis(labelFontSize=11)
            )
            st.altair_chart(timeline, use_container_width=True)
            st.markdown(f"<div style='color:#8B949E;font-size:11px;font-family:IBM Plex Mono,monospace;'>🟡 Gold dot = selected alert &nbsp;·&nbsp; Red = High &nbsp;·&nbsp; Orange = Medium &nbsp;·&nbsp; Green = Low</div>", unsafe_allow_html=True)
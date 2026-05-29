"""
Alerts Management Page — Interactive alert management with stats, search, and pagination.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from dashboard.api_client import get_alerts, update_alert_status, get_alert_rules


def render(auto_refresh: bool = True, refresh_interval: int = 15):
    if auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, key="alerts_refresh")

    st.markdown("# 🚨 Alert Management")

    try:
        all_alerts = get_alerts(limit=500)
        rules = get_alert_rules()
    except Exception as e:
        st.error(f"⚠️ Cannot connect to API: {e}")
        return

    if not all_alerts:
        st.info("No alerts triggered yet. The system is healthy! 🎉")
        return

    df = pd.DataFrame(all_alerts)

    # ─── Summary Stats ───────────────────────────────────────────────────────
    active_count = len(df[df["status"] == "active"])
    ack_count = len(df[df["status"] == "acknowledged"])
    resolved_count = len(df[df["status"] == "resolved"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔴 Active", active_count)
    col2.metric("🟡 Acknowledged", ack_count)
    col3.metric("✅ Resolved", resolved_count)
    col4.metric("📊 Total", len(df))

    # ─── Alert Distribution Chart ────────────────────────────────────────────
    st.markdown("---")
    tab_chart, tab_timeline = st.tabs(["📊 Distribution", "📈 Timeline"])

    with tab_chart:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            status_counts = df["status"].value_counts().reset_index()
            status_counts.columns = ["status", "count"]
            fig = go.Figure(data=[go.Pie(
                labels=status_counts["status"],
                values=status_counts["count"],
                hole=0.5,
                marker_colors=["#e74c3c", "#f1c40f", "#2ecc71"],
                textinfo="label+value",
            )])
            fig.update_layout(height=280, margin=dict(t=20, b=20, l=20, r=20), title_text="By Status")
            st.plotly_chart(fig, use_container_width=True)

        with col_c2:
            # Alerts by rule
            rule_map = {r["id"]: r["name"] for r in rules}
            df["rule_name"] = df["rule_id"].map(rule_map).fillna("Unknown")
            rule_counts = df["rule_name"].value_counts().reset_index()
            rule_counts.columns = ["rule", "count"]
            fig = px.bar(rule_counts, x="rule", y="count", color="count",
                         color_continuous_scale="Reds", title="By Rule")
            fig.update_layout(height=280, margin=dict(t=40, b=40, l=40, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab_timeline:
        df["triggered_at"] = pd.to_datetime(df["triggered_at"])
        df["hour"] = df["triggered_at"].dt.floor("h")
        timeline = df.groupby(["hour", "status"]).size().reset_index(name="count")
        fig = px.bar(timeline, x="hour", y="count", color="status",
                     color_discrete_map={"active": "#e74c3c", "acknowledged": "#f1c40f", "resolved": "#2ecc71"},
                     barmode="stack")
        fig.update_layout(height=300, hovermode="x unified", margin=dict(t=20, b=40, l=40, r=20))
        st.plotly_chart(fig, use_container_width=True)

    # ─── Filters & Search ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔎 Filter Alerts")

    col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 1.5, 1])
    with col_f1:
        status_filter = st.selectbox("Status", ["All", "active", "acknowledged", "resolved"], index=0)
    with col_f2:
        rule_filter = st.selectbox("Rule", ["All"] + list(rule_map.values()), index=0)
    with col_f3:
        search_text = st.text_input("Search message", "", placeholder="Type to search...")
    with col_f4:
        page_size = st.selectbox("Per page", [5, 10, 25, 50], index=1, key="alert_page_size")

    # Apply filters
    filtered_df = df.copy()
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]
    if rule_filter != "All":
        filtered_df = filtered_df[filtered_df["rule_name"] == rule_filter]
    if search_text:
        filtered_df = filtered_df[filtered_df["message"].str.contains(search_text, case=False, na=False)]

    filtered_df = filtered_df.sort_values("triggered_at", ascending=False).reset_index(drop=True)

    if filtered_df.empty:
        st.info("No alerts match your filters.")
        return

    # ─── Pagination ──────────────────────────────────────────────────────────
    if "alert_page" not in st.session_state:
        st.session_state.alert_page = 0

    total_results = len(filtered_df)
    total_pages = max(1, (total_results + page_size - 1) // page_size)

    # Reset page if out of bounds
    if st.session_state.alert_page >= total_pages:
        st.session_state.alert_page = 0

    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("⬅️ Prev", disabled=(st.session_state.alert_page == 0), key="alert_prev"):
            st.session_state.alert_page -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f'<div style="text-align:center;padding:8px;">'
            f'Page <strong>{st.session_state.alert_page + 1}</strong> of <strong>{total_pages}</strong> '
            f'({total_results} alerts)'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next ➡️", disabled=(st.session_state.alert_page >= total_pages - 1), key="alert_next"):
            st.session_state.alert_page += 1
            st.rerun()

    # ─── Alert Cards ─────────────────────────────────────────────────────────
    start_idx = st.session_state.alert_page * page_size
    end_idx = start_idx + page_size
    page_alerts = filtered_df.iloc[start_idx:end_idx]

    for _, alert in page_alerts.iterrows():
        status = alert["status"]
        icon = {"active": "🔴", "acknowledged": "🟡", "resolved": "✅"}.get(status, "⚪")
        border_color = {"active": "#e74c3c", "acknowledged": "#f1c40f", "resolved": "#2ecc71"}.get(status, "#95a5a6")

        st.markdown(
            f'<div style="border-left:4px solid {border_color};padding:12px 16px;margin-bottom:8px;'
            f'background:rgba(0,0,0,0.02);border-radius:6px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span>{icon} <strong>Alert #{int(alert["id"])}</strong> — {alert["rule_name"]}</span>'
            f'<span style="color:#7f8c8d;font-size:0.85em;">{alert["triggered_at"]}</span>'
            f'</div>'
            f'<div style="color:#555;margin-top:4px;font-size:0.9em;">{alert["message"][:120]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Action buttons
        if status == "active":
            col_a, col_b, _ = st.columns([1, 1, 4])
            with col_a:
                if st.button("Acknowledge", key=f"ack_{int(alert['id'])}"):
                    update_alert_status(int(alert["id"]), "acknowledged")
                    st.rerun()
            with col_b:
                if st.button("Resolve", key=f"res_{int(alert['id'])}"):
                    update_alert_status(int(alert["id"]), "resolved")
                    st.rerun()
        elif status == "acknowledged":
            col_a, _ = st.columns([1, 5])
            with col_a:
                if st.button("Resolve", key=f"res_{int(alert['id'])}"):
                    update_alert_status(int(alert["id"]), "resolved")
                    st.rerun()

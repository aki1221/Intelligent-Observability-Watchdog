"""
Health Trends Page — Visualize system health over time, breach patterns, webhook logs.
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from dashboard.api_client import (
    trigger_watchdog, get_webhook_logs, get_health_snapshots, get_alerts, get_alert_rules,
)


def render(auto_refresh: bool = True, refresh_interval: int = 10):
    if auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, key="health_refresh")

    st.markdown("# 🏥 Health Trends & Watchdog")
    st.caption("Monitor system health, trigger watchdog evaluations, and view breach patterns")

    # ─── Watchdog Control Panel ──────────────────────────────────────────────
    st.markdown("### ⚡ Watchdog Control")

    col_trigger, col_status = st.columns([1, 3])
    with col_trigger:
        if st.button("🔍 Run Watchdog Now", type="primary", use_container_width=True):
            try:
                result = trigger_watchdog()
                if result["breaches_detected"] > 0:
                    st.error(f"🚨 {result['breaches_detected']} breach(es) detected!")
                    for breach in result["breaches"]:
                        st.warning(
                            f"**{breach['rule_name']}**: {breach['actual_count']} events "
                            f"(threshold: {breach['threshold']}) in {breach['window_minutes']}m"
                        )
                else:
                    st.success("✅ No breaches detected. System healthy!")
            except Exception as e:
                st.error(f"Failed to run watchdog: {e}")

    with col_status:
        st.info(
            "The watchdog evaluates all enabled alert rules against recent events. "
            "When thresholds are breached, it triggers alerts and fires webhook notifications."
        )

    st.markdown("---")

    # ─── Health Trend Charts ─────────────────────────────────────────────────
    st.markdown("### 📈 Health Trends")

    try:
        hours_back = st.select_slider(
            "Time Range",
            options=[1, 3, 6, 12, 24, 48, 72],
            value=24,
            key="health_hours",
        )
        snapshots = get_health_snapshots(hours=hours_back)
    except Exception as e:
        st.warning(f"Cannot load health snapshots: {e}")
        snapshots = []

    if snapshots:
        df = pd.DataFrame(snapshots)
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Multi-axis health chart
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Event Rate (per hour)", "Error & Critical Count",
                "Active Alerts", "Breaches Detected"
            ),
            vertical_spacing=0.12,
            horizontal_spacing=0.08,
        )

        # Event rate
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=df["total_events_1h"],
                mode="lines+markers", name="Events/hr",
                line=dict(color="#3498db", width=2),
                fill="tozeroy", fillcolor="rgba(52,152,219,0.1)",
            ),
            row=1, col=1,
        )

        # Errors + Critical
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=df["error_count_1h"],
                mode="lines+markers", name="Errors",
                line=dict(color="#e74c3c", width=2),
            ),
            row=1, col=2,
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=df["critical_count_1h"],
                mode="lines+markers", name="Critical",
                line=dict(color="#9b59b6", width=2),
            ),
            row=1, col=2,
        )

        # Active alerts
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"], y=df["active_alerts"],
                mode="lines+markers", name="Active Alerts",
                line=dict(color="#f39c12", width=2),
                fill="tozeroy", fillcolor="rgba(243,156,18,0.1)",
            ),
            row=2, col=1,
        )

        # Breaches
        fig.add_trace(
            go.Bar(
                x=df["timestamp"], y=df["breaches"],
                name="Breaches",
                marker_color="#e74c3c",
            ),
            row=2, col=2,
        )

        fig.update_layout(
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=40, b=60, l=40, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Stats summary
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Avg Events/hr", f"{df['total_events_1h'].mean():.0f}")
        col2.metric("Peak Errors/hr", f"{df['error_count_1h'].max()}")
        col3.metric("Total Breaches", f"{df['breaches'].sum()}")
        col4.metric("Max Active Alerts", f"{df['active_alerts'].max()}")

    else:
        st.info(
            "No health snapshots yet. Click **Run Watchdog Now** above to generate the first snapshot, "
            "or snapshots are created automatically each watchdog cycle."
        )

    st.markdown("---")

    # ─── Webhook Logs ────────────────────────────────────────────────────────
    st.markdown("### 📬 Webhook Delivery Log")

    try:
        webhook_logs = get_webhook_logs(limit=50)
    except Exception as e:
        st.warning(f"Cannot load webhook logs: {e}")
        webhook_logs = []

    if webhook_logs:
        # Stats
        delivered_count = sum(1 for w in webhook_logs if w["delivered"])
        failed_count = len(webhook_logs) - delivered_count

        col1, col2, col3 = st.columns(3)
        col1.metric("📬 Total Webhooks", len(webhook_logs))
        col2.metric("✅ Delivered", delivered_count)
        col3.metric("❌ Failed", failed_count)

        # Table
        df_wh = pd.DataFrame(webhook_logs)
        df_wh["status"] = df_wh["delivered"].apply(lambda x: "✅ Delivered" if x else "❌ Failed")
        display_cols = ["id", "created_at", "rule_name", "alert_id", "status_code", "status", "response_body"]
        available_cols = [c for c in display_cols if c in df_wh.columns]

        st.dataframe(
            df_wh[available_cols],
            use_container_width=True,
            hide_index=True,
        )

        # Expandable payload viewer
        with st.expander("🔍 View Webhook Payloads"):
            selected_wh = st.selectbox(
                "Select webhook log",
                webhook_logs,
                format_func=lambda x: f"#{x['id']} — {x['rule_name']} ({x['created_at']})",
                key="wh_select",
            )
            if selected_wh:
                st.markdown(f"**Rule:** {selected_wh['rule_name']}")
                st.markdown(f"**Alert ID:** {selected_wh['alert_id']}")
                st.markdown(f"**Status Code:** {selected_wh['status_code']}")
                st.markdown(f"**Response:** {selected_wh['response_body']}")
    else:
        st.info("No webhook logs yet. Trigger the watchdog to generate breach notifications.")

    st.markdown("---")

    # ─── Breach History ──────────────────────────────────────────────────────
    st.markdown("### 🔥 Recent Breach Alerts")

    try:
        alerts = get_alerts(status="active", limit=20)
        rules = get_alert_rules()
        rule_map = {r["id"]: r["name"] for r in rules}
    except Exception as e:
        st.warning(f"Cannot load alerts: {e}")
        return

    breach_alerts = [a for a in alerts if "BREACHED" in a.get("message", "")]

    if breach_alerts:
        for alert in breach_alerts[:10]:
            rule_name = rule_map.get(alert["rule_id"], "Unknown")
            st.markdown(
                f'<div style="border-left:4px solid #e74c3c;padding:10px 14px;margin-bottom:8px;'
                f'border-radius:6px;background:rgba(231,76,60,0.05);">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<strong>🚨 {rule_name}</strong>'
                f'<span style="color:#7f8c8d;font-size:0.85em;">{alert["triggered_at"]}</span>'
                f'</div>'
                f'<div style="margin-top:4px;color:#555;">{alert["message"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.success("No active breach alerts. System is within thresholds. 🎉")

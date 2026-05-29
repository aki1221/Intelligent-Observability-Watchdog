"""
Dashboard Overview Page — KPIs, interactive charts, stats.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from dashboard.api_client import get_system_state, get_events


def render(auto_refresh: bool = True, refresh_interval: int = 10):
    if auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, key="overview_refresh")

    st.markdown("# 📊 System Overview")

    try:
        state = get_system_state()
    except Exception as e:
        st.error(f"⚠️ Cannot connect to API: {e}")
        st.info("Make sure the FastAPI server is running: `.venv/bin/uvicorn app.main:app --reload`")
        return

    # ─── KPI Metrics Row ─────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Events", f"{state['total_events']:,}")
    col2.metric("⏱️ Events (1h)", f"{state['events_last_hour']:,}")
    col3.metric("🚨 Active Alerts", state["active_alerts"])
    col4.metric("📋 Active Rules", state["active_rules"])

    st.markdown("")

    # ─── Fetch events for charts ─────────────────────────────────────────────
    events = get_events(limit=1000)
    if not events:
        st.info("No events in the system yet. Ingest some events to see charts.")
        return

    df = pd.DataFrame(events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # ─── Interactive Charts Row ──────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📈 Timeline", "🍩 Breakdown", "📊 Sources"])

    with tab1:
        st.markdown("#### Event Timeline")
        # Time granularity selector
        granularity = st.select_slider(
            "Time Granularity",
            options=["5min", "15min", "1h", "3h", "6h"],
            value="1h",
            key="timeline_granularity",
        )
        freq_map = {"5min": "5min", "15min": "15min", "1h": "h", "3h": "3h", "6h": "6h"}
        df["bucket"] = df["timestamp"].dt.floor(freq_map[granularity])

        timeline = df.groupby(["bucket", "severity"]).size().reset_index(name="count")

        fig = px.area(
            timeline,
            x="bucket",
            y="count",
            color="severity",
            color_discrete_map={
                "info": "#3498db",
                "warning": "#f1c40f",
                "error": "#e74c3c",
                "critical": "#9b59b6",
            },
            labels={"bucket": "Time", "count": "Events", "severity": "Severity"},
        )
        fig.update_layout(
            height=400,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=30, b=40, l=40, r=20),
        )
        fig.update_traces(hovertemplate="%{y} events")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        col_pie1, col_pie2 = st.columns(2)

        with col_pie1:
            st.markdown("#### Severity Distribution")
            severity_counts = df["severity"].value_counts().reset_index()
            severity_counts.columns = ["severity", "count"]

            fig = go.Figure(data=[go.Pie(
                labels=severity_counts["severity"],
                values=severity_counts["count"],
                hole=0.45,
                marker_colors=["#3498db", "#f1c40f", "#e74c3c", "#9b59b6"],
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>",
            )])
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_pie2:
            st.markdown("#### Event Type Distribution")
            type_counts = df["event_type"].value_counts().head(8).reset_index()
            type_counts.columns = ["event_type", "count"]

            fig = go.Figure(data=[go.Pie(
                labels=type_counts["event_type"],
                values=type_counts["count"],
                hole=0.45,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percent: %{percent}<extra></extra>",
            )])
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("#### Events by Source")
        source_severity = df.groupby(["source", "severity"]).size().reset_index(name="count")

        fig = px.bar(
            source_severity,
            x="source",
            y="count",
            color="severity",
            color_discrete_map={
                "info": "#3498db",
                "warning": "#f1c40f",
                "error": "#e74c3c",
                "critical": "#9b59b6",
            },
            barmode="stack",
            labels={"source": "Service", "count": "Events", "severity": "Severity"},
        )
        fig.update_layout(
            height=400,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=30, b=40, l=40, r=20),
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ─── Stats Summary Cards ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 Quick Stats")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        top_source = df["source"].value_counts().idxmax() if not df.empty else "N/A"
        st.markdown(f"""
        <div style="background:#2d3436;padding:15px;border-radius:10px;text-align:center;">
            <div style="color:#74b9ff;font-size:0.8em;">TOP SOURCE</div>
            <div style="color:white;font-size:1.2em;font-weight:bold;">{top_source}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        top_type = df["event_type"].value_counts().idxmax() if not df.empty else "N/A"
        st.markdown(f"""
        <div style="background:#2d3436;padding:15px;border-radius:10px;text-align:center;">
            <div style="color:#a29bfe;font-size:0.8em;">TOP EVENT TYPE</div>
            <div style="color:white;font-size:1.2em;font-weight:bold;">{top_type}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        error_pct = (len(df[df["severity"].isin(["error", "critical"])]) / len(df) * 100) if len(df) > 0 else 0
        st.markdown(f"""
        <div style="background:#2d3436;padding:15px;border-radius:10px;text-align:center;">
            <div style="color:#fd79a8;font-size:0.8em;">ERROR RATE</div>
            <div style="color:white;font-size:1.2em;font-weight:bold;">{error_pct:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        unique_sources = df["source"].nunique()
        st.markdown(f"""
        <div style="background:#2d3436;padding:15px;border-radius:10px;text-align:center;">
            <div style="color:#00cec9;font-size:0.8em;">ACTIVE SERVICES</div>
            <div style="color:white;font-size:1.2em;font-weight:bold;">{unique_sources}</div>
        </div>
        """, unsafe_allow_html=True)

"""
Live Feed Page — Real-time event stream with interactive filtering.
"""

import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from dashboard.api_client import get_events


def render():
    # Fast refresh for live feel
    count = st_autorefresh(interval=3_000, key="live_feed_refresh")

    st.markdown("# 📡 Live Event Feed")

    # ─── Connection Status Bar ───────────────────────────────────────────────
    col_status, col_refresh = st.columns([4, 1])
    with col_status:
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;">'
            '<span style="width:10px;height:10px;border-radius:50%;background:#2ecc71;'
            'display:inline-block;animation:pulse 2s infinite;"></span>'
            '<span style="color:#2ecc71;font-weight:600;">Live</span>'
            '<span style="color:#7f8c8d;margin-left:8px;">Polling every 3s</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    with col_refresh:
        st.markdown(f'<div style="text-align:right;color:#7f8c8d;">Refresh #{count}</div>', unsafe_allow_html=True)

    st.markdown("")

    # ─── Filters ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])
    with col1:
        severity_filter = st.selectbox("Severity", ["All", "info", "warning", "error", "critical"], index=0, key="live_sev")
    with col2:
        source_filter = st.text_input("Source", "", key="live_src", placeholder="Filter by source...")
    with col3:
        limit = st.selectbox("Show", [20, 50, 100], index=0, key="live_limit")
    with col4:
        compact_view = st.checkbox("Compact", value=False, key="live_compact")

    try:
        severity_param = None if severity_filter == "All" else severity_filter
        source_param = source_filter if source_filter else None
        events = get_events(source=source_param, severity=severity_param, limit=limit)
    except Exception as e:
        st.error(f"⚠️ Cannot connect to API: {e}")
        return

    if not events:
        st.info("⏳ Waiting for events...")
        return

    # ─── Live Stats Sparkline ────────────────────────────────────────────────
    df = pd.DataFrame(events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    severity_counts = df["severity"].value_counts()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ℹ️ Info", severity_counts.get("info", 0))
    col2.metric("⚠️ Warning", severity_counts.get("warning", 0))
    col3.metric("❌ Error", severity_counts.get("error", 0))
    col4.metric("💀 Critical", severity_counts.get("critical", 0))

    st.markdown("---")

    # ─── Event Stream ────────────────────────────────────────────────────────
    color_map = {"info": "#3498db", "warning": "#f1c40f", "error": "#e74c3c", "critical": "#9b59b6"}
    icon_map = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "💀"}

    for event in events:
        severity = event["severity"]
        color = color_map.get(severity, "#95a5a6")
        icon = icon_map.get(severity, "⚪")

        if compact_view:
            st.markdown(
                f'<div style="border-left:3px solid {color};padding:4px 10px;margin-bottom:4px;'
                f'font-size:0.85em;border-radius:3px;">'
                f'{icon} <strong>{event["source"]}</strong> '
                f'<span style="color:#7f8c8d;">|</span> {event["message"][:80]} '
                f'<span style="color:#7f8c8d;float:right;">{event["timestamp"][-8:]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            # Parse metadata
            try:
                metadata = json.loads(event.get("metadata_json", "{}"))
                meta_pills = " ".join(
                    f'<span style="background:rgba(255,255,255,0.1);padding:2px 6px;'
                    f'border-radius:4px;font-size:0.75em;color:#b2bec3;">{k}={v}</span>'
                    for k, v in metadata.items()
                ) if metadata else ""
            except (json.JSONDecodeError, TypeError):
                meta_pills = ""

            st.markdown(
                f'<div style="border-left:4px solid {color};padding:10px 14px;margin-bottom:6px;'
                f'background:rgba(0,0,0,0.02);border-radius:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span>{icon} <strong>[{event["source"]}]</strong> '
                f'<span style="color:#636e72;">{event["event_type"]}</span></span>'
                f'<span style="color:#7f8c8d;font-size:0.8em;">{event["timestamp"]}</span>'
                f'</div>'
                f'<div style="margin-top:4px;color:#2d3436;">{event["message"]}</div>'
                f'{"<div style=margin-top:6px;>" + meta_pills + "</div>" if meta_pills else ""}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ─── WebSocket Info ──────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("ℹ️ WebSocket Integration"):
        st.markdown("""
        **WebSocket Endpoint:** `ws://localhost:8000/ws/events`

        ```python
        import asyncio, websockets, json

        async def listen():
            async with websockets.connect("ws://localhost:8000/ws/events") as ws:
                while True:
                    msg = await ws.recv()
                    event = json.loads(msg)
                    print(f"[{event['data']['severity']}] {event['data']['message']}")

        asyncio.run(listen())
        ```
        """)

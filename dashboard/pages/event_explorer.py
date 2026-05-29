"""
Event Explorer Page — Searchable, filterable, paginated event table with interactive charts.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import json
from streamlit_autorefresh import st_autorefresh
from dashboard.api_client import get_events


def render(auto_refresh: bool = True, refresh_interval: int = 10):
    if auto_refresh:
        st_autorefresh(interval=refresh_interval * 1000, key="explorer_refresh")

    st.markdown("# 🔍 Event Explorer")
    st.caption("Search, filter, and explore all events with pagination")

    # ─── Filters Bar ─────────────────────────────────────────────────────────
    with st.container():
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1])

        with col1:
            search_text = st.text_input("🔎 Search messages", "", placeholder="Type to search...")
        with col2:
            source_filter = st.text_input("📦 Source", "", placeholder="e.g., payment-service")
        with col3:
            severity_filter = st.selectbox(
                "⚡ Severity",
                ["All", "info", "warning", "error", "critical"],
                index=0,
            )
        with col4:
            event_type_filter = st.text_input("🏷️ Event Type", "", placeholder="e.g., http_error")
        with col5:
            page_size = st.selectbox("Per page", [10, 25, 50, 100], index=1)

    # ─── Pagination State ────────────────────────────────────────────────────
    if "explorer_page" not in st.session_state:
        st.session_state.explorer_page = 0

    try:
        # Fetch a large batch for client-side filtering
        severity_param = None if severity_filter == "All" else severity_filter
        source_param = source_filter if source_filter else None

        all_events = get_events(
            source=source_param,
            event_type=event_type_filter if event_type_filter else None,
            severity=severity_param,
            limit=1000,
        )
    except Exception as e:
        st.error(f"⚠️ Cannot connect to API: {e}")
        return

    if not all_events:
        st.info("No events found matching your filters.")
        return

    df = pd.DataFrame(all_events)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Client-side text search
    if search_text:
        mask = df["message"].str.contains(search_text, case=False, na=False)
        df = df[mask]

    if df.empty:
        st.info("No events match your search criteria.")
        return

    # ─── Stats Bar ───────────────────────────────────────────────────────────
    total_results = len(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Results", f"{total_results:,}")
    col2.metric("🔴 Errors", len(df[df["severity"] == "error"]))
    col3.metric("🟣 Critical", len(df[df["severity"] == "critical"]))
    col4.metric("Sources", df["source"].nunique())

    st.markdown("---")

    # ─── Interactive Chart ───────────────────────────────────────────────────
    with st.expander("📈 Event Distribution Chart", expanded=True):
        chart_type = st.radio(
            "Chart type",
            ["Timeline", "By Source", "By Type", "Heatmap"],
            horizontal=True,
            key="explorer_chart_type",
        )

        if chart_type == "Timeline":
            df_chart = df.copy()
            df_chart["hour"] = df_chart["timestamp"].dt.floor("h")
            timeline = df_chart.groupby(["hour", "severity"]).size().reset_index(name="count")
            fig = px.line(
                timeline, x="hour", y="count", color="severity",
                color_discrete_map={"info": "#3498db", "warning": "#f1c40f", "error": "#e74c3c", "critical": "#9b59b6"},
                markers=True,
            )
            fig.update_layout(height=300, hovermode="x unified", margin=dict(t=20, b=40, l=40, r=20))
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "By Source":
            source_counts = df["source"].value_counts().reset_index()
            source_counts.columns = ["source", "count"]
            fig = px.bar(source_counts, x="source", y="count", color="count",
                         color_continuous_scale="Viridis")
            fig.update_layout(height=300, margin=dict(t=20, b=40, l=40, r=20))
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "By Type":
            type_counts = df["event_type"].value_counts().reset_index()
            type_counts.columns = ["event_type", "count"]
            fig = px.treemap(type_counts, path=["event_type"], values="count",
                             color="count", color_continuous_scale="RdYlBu_r")
            fig.update_layout(height=350, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

        elif chart_type == "Heatmap":
            df_heat = df.copy()
            df_heat["hour"] = df_heat["timestamp"].dt.hour
            df_heat["day"] = df_heat["timestamp"].dt.day_name()
            heatmap_data = df_heat.groupby(["day", "hour"]).size().reset_index(name="count")
            fig = px.density_heatmap(
                heatmap_data, x="hour", y="day", z="count",
                color_continuous_scale="YlOrRd",
                labels={"hour": "Hour of Day", "day": "Day", "count": "Events"},
            )
            fig.update_layout(height=300, margin=dict(t=20, b=40, l=80, r=20))
            st.plotly_chart(fig, use_container_width=True)

    # ─── Paginated Table ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Events Table")

    total_pages = max(1, (total_results + page_size - 1) // page_size)

    # Pagination controls
    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("⬅️ Previous", disabled=(st.session_state.explorer_page == 0)):
            st.session_state.explorer_page -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f'<div style="text-align:center;padding:8px;">'
            f'Page <strong>{st.session_state.explorer_page + 1}</strong> of <strong>{total_pages}</strong> '
            f'({total_results} results)'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Next ➡️", disabled=(st.session_state.explorer_page >= total_pages - 1)):
            st.session_state.explorer_page += 1
            st.rerun()

    # Slice data for current page
    start_idx = st.session_state.explorer_page * page_size
    end_idx = start_idx + page_size
    page_df = df.iloc[start_idx:end_idx]

    # Format for display
    display_df = page_df[["id", "timestamp", "source", "event_type", "severity", "message"]].copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Severity badges
    def severity_badge(sev):
        icons = {"info": "🔵", "warning": "🟡", "error": "🔴", "critical": "🟣"}
        return f"{icons.get(sev, '⚪')} {sev}"

    display_df["severity"] = display_df["severity"].apply(severity_badge)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
            "source": st.column_config.TextColumn("Source", width="medium"),
            "event_type": st.column_config.TextColumn("Type", width="medium"),
            "severity": st.column_config.TextColumn("Severity", width="small"),
            "message": st.column_config.TextColumn("Message", width="large"),
        },
    )

    # ─── Event Detail Expander ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🔎 Event Details")
    st.caption("Click an event ID below to see full metadata")

    selected_id = st.selectbox(
        "Select Event ID",
        page_df["id"].tolist(),
        index=0,
        key="event_detail_select",
    )

    if selected_id:
        event_row = page_df[page_df["id"] == selected_id].iloc[0]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Source:** `{event_row['source']}`")
            st.markdown(f"**Type:** `{event_row['event_type']}`")
            st.markdown(f"**Severity:** {severity_badge(event_row['severity'] if 'severity' in event_row else 'info')}")
            st.markdown(f"**Timestamp:** {event_row['timestamp']}")
        with col2:
            st.markdown("**Message:**")
            st.code(event_row["message"], language=None)
            try:
                metadata = json.loads(event_row.get("metadata_json", "{}"))
                if metadata:
                    st.markdown("**Metadata:**")
                    st.json(metadata)
            except (json.JSONDecodeError, TypeError):
                pass

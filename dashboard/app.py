"""
Intelligent Observability Dashboard
Run with: streamlit run dashboard/app.py
"""

import sys
import os

# Ensure the project root is on sys.path so absolute imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="Observability Watchdog",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS for better styling ──────────────────────────────────────────
st.markdown("""
<style>
    /* Hide default Streamlit nav links */
    [data-testid="stSidebarNavLinkContainer"] {
        display: none !important;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px 20px;
        border-radius: 12px;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    [data-testid="stMetric"] label {
        color: rgba(255,255,255,0.8) !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: white !important;
        font-size: 2rem !important;
    }

    /* Tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }

    /* Expander */
    .streamlit-expanderHeader {
        border-radius: 8px;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar Navigation ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔭 Observability Watchdog")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📊 Dashboard", "🚨 Alerts", "📋 Rules", "📡 Live Feed", "🔍 Event Explorer", "🏥 Health Trends"],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("##### ⚙️ Settings")
    auto_refresh = st.checkbox("Auto-refresh", value=True)
    refresh_interval = st.select_slider(
        "Interval (sec)",
        options=[3, 5, 10, 15, 30, 60],
        value=10,
    )

    st.markdown("---")
    st.markdown(
        '<div style="text-align:center;color:#7f8c8d;font-size:0.8em;">'
        'v0.1.0 • API-first Observability'
        '</div>',
        unsafe_allow_html=True,
    )

# ─── Page Routing ────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    from dashboard.pages import overview
    overview.render(auto_refresh, refresh_interval)
elif page == "🚨 Alerts":
    from dashboard.pages import alerts_page
    alerts_page.render(auto_refresh, refresh_interval)
elif page == "📋 Rules":
    from dashboard.pages import rules_page
    rules_page.render()
elif page == "📡 Live Feed":
    from dashboard.pages import live_feed
    live_feed.render()
elif page == "🔍 Event Explorer":
    from dashboard.pages import event_explorer
    event_explorer.render(auto_refresh, refresh_interval)
elif page == "🏥 Health Trends":
    from dashboard.pages import health_trends
    health_trends.render(auto_refresh, refresh_interval)

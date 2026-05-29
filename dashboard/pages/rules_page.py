"""
Rules Management Page — Create, edit, enable/disable, and delete alert rules with search.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.api_client import get_alert_rules, create_alert_rule, update_alert_rule, delete_alert_rule


def render():
    st.markdown("# 📋 Alert Rules Management")
    st.caption("Create and manage alert rules that trigger notifications")

    try:
        rules = get_alert_rules()
    except Exception as e:
        st.error(f"⚠️ Cannot connect to API: {e}")
        return

    # ─── Stats Row ───────────────────────────────────────────────────────────
    if rules:
        enabled_count = sum(1 for r in rules if r["enabled"])
        disabled_count = len(rules) - enabled_count

        col1, col2, col3 = st.columns(3)
        col1.metric("📋 Total Rules", len(rules))
        col2.metric("🟢 Enabled", enabled_count)
        col3.metric("🔴 Disabled", disabled_count)

        # Quick chart
        with st.expander("📊 Rules by Event Type", expanded=False):
            df_rules = pd.DataFrame(rules)
            type_counts = df_rules["event_type"].value_counts().reset_index()
            type_counts.columns = ["event_type", "count"]
            fig = px.bar(type_counts, x="event_type", y="count", color="event_type",
                         title="Rules per Event Type")
            fig.update_layout(height=250, margin=dict(t=40, b=40, l=40, r=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ─── Create New Rule ─────────────────────────────────────────────────────
    with st.expander("➕ Create New Rule", expanded=False):
        with st.form("create_rule_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Rule Name *", placeholder="e.g., High Error Rate")
                event_type = st.text_input("Event Type *", placeholder="e.g., http_error")
                condition = st.text_input("Condition *", placeholder="e.g., count > 10 in 5m")
            with col2:
                description = st.text_area("Description", placeholder="What does this rule detect?", height=68)
                severity_threshold = st.selectbox(
                    "Severity Threshold",
                    ["info", "warning", "error", "critical"],
                    index=2,
                )
                enabled = st.checkbox("Enabled", value=True)

            submitted = st.form_submit_button("🚀 Create Rule", type="primary", use_container_width=True)
            if submitted:
                if not name or not event_type or not condition:
                    st.error("Name, Event Type, and Condition are required.")
                else:
                    try:
                        create_alert_rule({
                            "name": name,
                            "event_type": event_type,
                            "condition": condition,
                            "description": description,
                            "severity_threshold": severity_threshold,
                            "enabled": enabled,
                        })
                        st.success(f"✅ Rule '{name}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create rule: {e}")

    st.markdown("---")

    # ─── Search & Filter ─────────────────────────────────────────────────────
    st.markdown("#### 📜 Existing Rules")

    if not rules:
        st.info("No alert rules configured yet. Create one above!")
        return

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        search = st.text_input("🔎 Search rules", "", placeholder="Search by name, type, or condition...")
    with col_s2:
        filter_status = st.selectbox("Status", ["All", "Enabled", "Disabled"], key="rule_status_filter")

    # Apply filters
    filtered_rules = rules
    if search:
        search_lower = search.lower()
        filtered_rules = [
            r for r in filtered_rules
            if search_lower in r["name"].lower()
            or search_lower in r["event_type"].lower()
            or search_lower in r["condition"].lower()
        ]
    if filter_status == "Enabled":
        filtered_rules = [r for r in filtered_rules if r["enabled"]]
    elif filter_status == "Disabled":
        filtered_rules = [r for r in filtered_rules if not r["enabled"]]

    st.caption(f"Showing {len(filtered_rules)} of {len(rules)} rules")

    # ─── Rules Table ─────────────────────────────────────────────────────────
    for rule in filtered_rules:
        status_icon = "🟢" if rule["enabled"] else "🔴"
        severity_colors = {"info": "#3498db", "warning": "#f1c40f", "error": "#e74c3c", "critical": "#9b59b6"}
        sev_color = severity_colors.get(rule["severity_threshold"], "#95a5a6")

        with st.expander(
            f"{status_icon} **{rule['name']}** — `{rule['event_type']}` | "
            f"`{rule['condition']}` | Threshold: {rule['severity_threshold']}"
        ):
            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"**ID:** {rule['id']}")
                st.markdown(f"**Description:** {rule.get('description') or 'N/A'}")
                st.markdown(f"**Event Type:** `{rule['event_type']}`")
                st.markdown(
                    f"**Severity Threshold:** "
                    f'<span style="color:{sev_color};font-weight:bold;">{rule["severity_threshold"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Condition:** `{rule['condition']}`")
                st.markdown(f"**Status:** {'✅ Enabled' if rule['enabled'] else '❌ Disabled'}")
                st.markdown(f"**Created:** {rule['created_at']}")

            with col_actions:
                st.markdown("**Actions:**")
                # Toggle enable/disable
                if rule["enabled"]:
                    if st.button("⏸️ Disable", key=f"disable_{rule['id']}", use_container_width=True):
                        update_alert_rule(rule["id"], {"enabled": False})
                        st.rerun()
                else:
                    if st.button("▶️ Enable", key=f"enable_{rule['id']}", use_container_width=True):
                        update_alert_rule(rule["id"], {"enabled": True})
                        st.rerun()

                st.markdown("")
                if st.button("🗑️ Delete", key=f"delete_{rule['id']}", use_container_width=True):
                    delete_alert_rule(rule["id"])
                    st.success("Deleted!")
                    st.rerun()

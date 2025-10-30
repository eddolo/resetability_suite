# ==========================================================
# app_resetability_live.py — Main Launcher (modular)
# ==========================================================
# Tabs:
#  - Live / Simulation (ui_live.render_live_tab)
#  - Analysis & Reports (ui_analysis.render_analysis_tab)
#  - Monte Carlo (ui_montecarlo.render_montecarlo_tab)
# Session-state rules:
#  - Never force sim_mode; always respect user’s last choice
#  - Domain selection persists via URL query parameters.
#  - Replay from Analysis sets state and reruns this script.
# ==========================================================

import streamlit as st

# --- Page config early ---
st.set_page_config(page_title="Resetability Control Suite", layout="wide")

# --- Domain modules ---
from python.domains import booster, gravity_test, robot, spacecraft
from python.ui_analysis import render_analysis_tab
from python.ui_live import render_live_tab
from python.ui_montecarlo import render_montecarlo_tab

DOMAIN_MAP = {
    "🦾 Robot": robot,
    "🛰️ Spacecraft": spacecraft,
    "🚀 Booster": booster,
    "🌍 Gravity Test": gravity_test,
}
DOMAIN_COLORS = {
    "🦾 Robot": "#64b5f6",
    "🛰️ Spacecraft": "#ce93d8",
    "🚀 Booster": "#ffb74d",
    "🌍 Gravity Test": "#81c784",
}

# ==========================================================
# Session State with Persistence
# ==========================================================
# Initialize session state keys if they don't exist
st.session_state.setdefault("sim_mode", True)
st.session_state.setdefault("running", False)
st.session_state.setdefault("sim_idx", 0)
st.session_state.setdefault("last_event_ts", -1e18)

# --- Persistence Logic for Selected Domain ---
query_params = st.query_params.to_dict()
domain_from_url = query_params.get("domain", [None])[0]

# 1. If a valid domain is in the URL, use it to set the session state.
if domain_from_url and domain_from_url in DOMAIN_MAP:
    st.session_state.selected_domain = domain_from_url
# 2. Otherwise, if the session state already has a domain, keep it.
# 3. If neither of the above, set it to the default.
else:
    st.session_state.setdefault("selected_domain", "🛰️ Spacecraft")

# Update the URL to reflect the current state (ensures consistency)
st.query_params["domain"] = st.session_state.selected_domain

# ==========================================================
# Header & Top Bar Controls
# ==========================================================
st.title("🧭 SO(3) Resetability Control Suite")

# --- Quick Domain Switcher ---
cols = st.columns(len(DOMAIN_MAP))
domain_keys = list(DOMAIN_MAP.keys())

for i, domain_key in enumerate(domain_keys):
    # Use the domain key as the button label and a unique key for the button itself
    if cols[i].button(domain_key, use_container_width=True, key=f"domain_switch_{i}"):
        # Check if the user clicked a button for a *different* domain
        if st.session_state.selected_domain != domain_key:
            st.session_state.selected_domain = domain_key
            # Update the URL parameter to maintain persistence
            st.query_params["domain"] = domain_key
            # Reset simulation on switch to avoid confusion
            st.session_state.sim_idx = 0
            st.session_state.running = False
            st.rerun()

st.markdown("---") # Visual separator

# ==========================================================
# Tabs
# ==========================================================
tab_live, tab_analysis, tab_mc = st.tabs(
    [
        "📡 Live / Simulation",
        "📊 Analysis & Reports",
        "🧪 Monte Carlo Simulation",
    ]
)

with tab_live:
    # The live tab handles sidebar controls, playback, plots, logging, etc.
    render_live_tab(st, DOMAIN_MAP, DOMAIN_COLORS)

with tab_analysis:
    # Full-featured analysis with JSON export + replay functionality
    render_analysis_tab(st, DOMAIN_COLORS)

with tab_mc:
    # Monte Carlo runner, cached for performance
    render_montecarlo_tab(st)

# ==========================================================
# Cross-tab replay bridge
# If analysis set a selected_event, the live tab will consume it on the next rerun.
# ==========================================================
if "selected_event" in st.session_state and st.session_state.selected_event:
    # No action needed here; the logic inside ui_live.py handles the event.
    pass
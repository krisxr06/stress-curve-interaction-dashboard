"""
Stress × Curve Interaction Dashboard
======================================
Main Streamlit application.

Sections
--------
1. Current Snapshot         — yields, spread, regime badges, stress metrics, summary
2. Stress by Curve Regime   — avg stress components across YC regimes
3. Stress × Curve Regime    — co-occurrence heatmap (centerpiece) + bullets
4. Curve Behavior Under Stress — spread and inversion stats by stress regime + summary
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.data_loader import load_all
from src.transforms  import apply_transforms
from src.regimes     import add_regimes
from src.charts      import stress_by_regime_chart, cooccurrence_heatmap, curve_under_stress_chart
from src.utils       import (
    latest_values,
    snapshot_summary,
    stress_by_regime_table,
    section3_bullets,
    curve_stress_table,
    section4_summary,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stress & Yield Curve Interaction",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="metric-container"] {
    background: #1a1d2e;
    border: 1px solid #2a2f45;
    border-radius: 10px;
    padding: 14px 18px 10px;
}
.badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 15px;
    font-weight: 600;
}
.badge-inverted   { background:#3a0e0e; color:#ff7070; border:1px solid #6b1f1f; }
.badge-resteep    { background:#362200; color:#ffb347; border:1px solid #6b4a00; }
.badge-flat       { background:#2e2900; color:#e8d44d; border:1px solid #5a5000; }
.badge-normal     { background:#0d2914; color:#5dde7c; border:1px solid #1e5c30; }
.badge-high       { background:#3a0e0e; color:#ff7070; border:1px solid #6b1f1f; }
.badge-moderate   { background:#362200; color:#ffb347; border:1px solid #6b4a00; }
.badge-low        { background:#0d1f2e; color:#5b9bd5; border:1px solid #1e3c5c; }
.badge-unknown    { background:#1e2030; color:#9da5b4; border:1px solid #3a3f55; }
.divider          { border-top:1px solid #2a2f45; margin:28px 0 20px; }
.caption-text     { font-size:13px; color:#9ca3b0; line-height:1.65; padding:6px 0 0; }
.disclaimer       { font-size:12px; color:#7a8299; font-style:italic; padding:6px 0 2px; }
</style>
""", unsafe_allow_html=True)


# ── Data ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_data() -> pd.DataFrame:
    return add_regimes(apply_transforms(load_all()))


with st.spinner("Fetching FRED data…"):
    df = get_data()

vals           = latest_values(df)
current_yc     = vals["yc_regime"]
current_stress = vals["stress_regime"]


# ── Header ─────────────────────────────────────────────────────────────────────
st.title("Stress & Yield Curve Interaction")
st.markdown("##### Market Stress Across Yield Curve Regimes — Historical Patterns and Current Positioning")
try:
    date_str = vals["date"].strftime("%B %Y")
except Exception:
    date_str = "latest available"
st.caption(f"Data through **{date_str}** · Source: FRED (DGS2, DGS10, FEDFUNDS, BAA10Y, VIXCLS)")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def _fmt(val, suffix="", decimals=2, signed=False):
    try:
        if pd.isna(val):
            return "N/A"
        sign = "+" if signed and float(val) >= 0 else ""
        return f"{sign}{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Current Snapshot
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1 — Current Snapshot")

c1, c2, c3, c4 = st.columns(4)
c1.metric("2Y Treasury",    _fmt(vals["dgs2"],     "%"))
c2.metric("10Y Treasury",   _fmt(vals["dgs10"],    "%"))
c3.metric("Fed Funds Rate", _fmt(vals["fedfunds"], "%"))
c4.metric("10Y–2Y Spread",  _fmt(vals["spread"],   " ppts", signed=True))

st.write("")

c5, c6, c7, c8 = st.columns(4)
c5.metric("BAA10Y Spread",  _fmt(vals["baa10y"],       "%"))
c6.metric("VIX",            _fmt(vals["vix"],           "", 1))
c7.metric("Stress Score",   _fmt(vals["stress_score"],  "", signed=True))

# Regime badges
_yc_badge = {
    "Inverted": "badge-inverted", "Re-steepening": "badge-resteep",
    "Flat": "badge-flat",         "Normal": "badge-normal",
}.get(current_yc, "badge-unknown")

_stress_badge = {
    "High Stress": "badge-high", "Moderate Stress": "badge-moderate",
    "Low Stress":  "badge-low",
}.get(current_stress, "badge-unknown")

with c8:
    st.markdown("**Regimes**")
    st.markdown(
        f"<span class='badge {_yc_badge}'>{current_yc}</span>&nbsp;"
        f"<span class='badge {_stress_badge}'>{current_stress}</span>",
        unsafe_allow_html=True,
    )

st.write("")
st.info(snapshot_summary(vals), icon="💡")
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Stress by Curve Regime
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("2 — Stress by Yield Curve Regime")

st.markdown(
    "<div class='disclaimer'>⚠ Stress z-scores are simplified descriptive proxies based on "
    "BAA10Y credit spread and VIXCLS. Not a risk model output.</div>",
    unsafe_allow_html=True,
)
st.write("")

st.plotly_chart(stress_by_regime_chart(df), use_container_width=True)

st.markdown("#### Average Stress Metrics by Regime (raw values)")
tbl = stress_by_regime_table(df)

def _highlight_yc(row):
    return ["background-color: #1a3a5c; font-weight:bold"] * len(row) if row.name == current_yc else [""] * len(row)

st.dataframe(tbl.style.apply(_highlight_yc, axis=1), use_container_width=True, hide_index=False)
st.markdown(
    "<div class='caption-text'>"
    "All z-scores computed over each series' full available history. "
    "Higher combined z-score = stress components further above historical average."
    "</div>",
    unsafe_allow_html=True,
)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Stress × Curve Regime Interaction
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("3 — Stress × Curve Regime Interaction")
st.plotly_chart(cooccurrence_heatmap(df, current_yc, current_stress), use_container_width=True)

st.markdown(
    "<div class='caption-text'>"
    "Each cell shows month count and % of total classified history. "
    "▶ NOW marks the current regime combination."
    "</div>",
    unsafe_allow_html=True,
)

st.write("")
st.markdown(section3_bullets(df, current_yc, current_stress))
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Curve Behavior Under Stress
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("4 — Curve Behavior Under Stress")

st.plotly_chart(curve_under_stress_chart(df), use_container_width=True)

st.markdown("#### Spread Statistics by Stress Regime")
stress_tbl = curve_stress_table(df)

def _highlight_stress(row):
    return ["background-color: #1a3a5c; font-weight:bold"] * len(row) if row.name == current_stress else [""] * len(row)

st.dataframe(stress_tbl.style.apply(_highlight_stress, axis=1), use_container_width=True, hide_index=False)

st.write("")
st.markdown(section4_summary(df, vals))

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption(
    "Data: Federal Reserve Economic Data (FRED) · "
    "Stress regimes are simplified rule-based classifications for educational purposes only · "
    "Not investment advice · Built with Streamlit & Plotly"
)

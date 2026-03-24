"""
Utility functions: latest values, regime statistics, and all dashboard text.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .regimes import YC_REGIMES, STRESS_REGIMES


# ── Helpers ────────────────────────────────────────────────────────────────────

def _is_nan(v) -> bool:
    try:
        return pd.isna(v)
    except (TypeError, ValueError):
        return False


def _fmt(val, suffix: str = "", decimals: int = 2, signed: bool = False) -> str:
    if _is_nan(val):
        return "N/A"
    sign = "+" if signed and float(val) >= 0 else ""
    return f"{sign}{float(val):.{decimals}f}{suffix}"


# ── Latest values ──────────────────────────────────────────────────────────────

def latest_values(df: pd.DataFrame) -> dict:
    def _last(col):
        if col not in df.columns:
            return float("nan")
        s = df[col].dropna()
        return s.iloc[-1] if not s.empty else float("nan")

    try:
        date = df[["DGS2", "DGS10"]].dropna(how="all").index[-1]
    except (IndexError, KeyError):
        date = df.index[-1] if not df.empty else pd.Timestamp.now()

    yc     = _last("yc_regime")
    stress = _last("stress_regime")

    return {
        "date":           date,
        "dgs2":           _last("DGS2"),
        "dgs10":          _last("DGS10"),
        "fedfunds":       _last("FEDFUNDS"),
        "spread":         _last("spread_10y2y"),
        "baa10y":         _last("BAA10Y"),
        "vix":            _last("VIXCLS"),
        "stress_score":   _last("combined_stress"),
        "yc_regime":      str(yc)     if not _is_nan(yc)     else "Unknown",
        "stress_regime":  str(stress) if not _is_nan(stress) else "Unknown",
    }


# ── Section 1: Snapshot summary ───────────────────────────────────────────────

def snapshot_summary(vals: dict) -> str:
    yc     = vals.get("yc_regime",     "Unknown")
    stress = vals.get("stress_regime", "Unknown")
    spread = vals.get("spread",        float("nan"))
    score  = vals.get("stress_score",  float("nan"))
    ff     = vals.get("fedfunds",      float("nan"))

    spread_s = _fmt(spread, " ppts", signed=True)
    score_s  = _fmt(score,  "",       decimals=2, signed=True)
    ff_s     = _fmt(ff,     "%")

    yc_map = {
        "Inverted":      f"Yield curve: **inverted** ({spread_s}).",
        "Re-steepening": f"Yield curve: **re-steepening** ({spread_s}) following a period of inversion.",
        "Flat":          f"Yield curve: **flat** ({spread_s}).",
        "Normal":        f"Yield curve: **normal** ({spread_s}).",
    }
    yc_sent = yc_map.get(yc, f"Yield curve regime: **{yc}** ({spread_s}).")

    stress_map = {
        "High Stress":     f"Stress regime: **High** (combined z-score: {score_s}) — historically associated with elevated credit spreads and equity volatility.",
        "Moderate Stress": f"Stress regime: **Moderate** (combined z-score: {score_s}) — conditions broadly in line with historical averages.",
        "Low Stress":      f"Stress regime: **Low** (combined z-score: {score_s}) — credit spreads and volatility below historical norms.",
    }
    stress_sent = stress_map.get(stress, f"Stress regime: **{stress}** (z-score: {score_s}).")

    disclaimer = (
        f"Fed Funds: **{ff_s}**. "
        "*This framework is descriptive rather than predictive — stress regimes "
        "are simplified rule-based classifications, not risk model outputs.*"
    )

    return f"{yc_sent}  \n{stress_sent}  \n{disclaimer}"


# ── Section 2: Stress by regime stats ─────────────────────────────────────────

def stress_by_regime_table(df: pd.DataFrame) -> pd.DataFrame:
    """Raw average stress metrics per YC regime for the summary table."""
    valid = df[df["yc_regime"].isin(YC_REGIMES)].copy()
    rows  = []
    for regime in YC_REGIMES:
        sub = valid[valid["yc_regime"] == regime]
        rows.append({
            "Regime":            regime,
            "Avg BAA10Y (%)":    round(sub["BAA10Y"].mean(),          2) if "BAA10Y"          in sub else "—",
            "Avg VIX":           round(sub["VIXCLS"].mean(),          1) if "VIXCLS"          in sub else "—",
            "Avg Stress (z)":    round(sub["combined_stress"].mean(), 2) if "combined_stress" in sub else "—",
            "Stress Volatility": round(sub["combined_stress"].std(),  2) if "combined_stress" in sub else "—",
            "n":                 sub["combined_stress"].dropna().shape[0],
        })
    return pd.DataFrame(rows).set_index("Regime")


# ── Section 3: Co-occurrence bullets ──────────────────────────────────────────

def section3_bullets(df: pd.DataFrame, current_yc: str, current_stress: str) -> str:
    """3–4 observational bullets for the heatmap section."""
    valid = df[
        df["yc_regime"].isin(YC_REGIMES) & df["stress_regime"].isin(STRESS_REGIMES)
    ].copy()
    total = len(valid)
    if total == 0:
        return "Insufficient data."

    def _pct(mask):
        return mask.sum() / total * 100

    # Inverted + High Stress
    inv_high = _pct(
        (valid["yc_regime"] == "Inverted") & (valid["stress_regime"] == "High Stress")
    )

    # Normal + Low Stress
    norm_low = _pct(
        (valid["yc_regime"] == "Normal") & (valid["stress_regime"] == "Low Stress")
    )

    # Normal + Moderate or Low combined
    norm_low_mod = _pct(
        (valid["yc_regime"] == "Normal") & valid["stress_regime"].isin(["Low Stress", "Moderate Stress"])
    )

    # Re-steepening + High Stress
    resteep_high = _pct(
        (valid["yc_regime"] == "Re-steepening") & (valid["stress_regime"] == "High Stress")
    )

    # Current combination
    cur_n   = len(valid[
        (valid["yc_regime"] == current_yc) & (valid["stress_regime"] == current_stress)
    ])
    cur_pct = cur_n / total * 100

    lines = [
        f"- **Normal + Low Stress** accounts for {norm_low:.0f}% of classified history — "
        "the most benign combination for fixed-income conditions.",

        f"- **Inverted + High Stress** has co-occurred {inv_high:.0f}% of the time — "
        "historically among the most stressed macro environments.",

        f"- **Normal regimes** coincide with Low or Moderate stress {norm_low_mod:.0f}% of classified months — "
        "high stress during normal curves has historically been the exception.",

        f"- **Current combination** (*{current_yc} / {current_stress}*): "
        f"{cur_n} of {total} classified months ({cur_pct:.0f}% of history).",
    ]
    return "  \n".join(lines)


# ── Section 4: Curve behavior under stress ────────────────────────────────────

def curve_stress_table(df: pd.DataFrame) -> pd.DataFrame:
    """Summary table: avg spread, avg spread change, % inverted by stress regime."""
    valid = df[df["stress_regime"].isin(STRESS_REGIMES)].copy()
    rows  = []
    for regime in STRESS_REGIMES:
        sub    = valid[valid["stress_regime"] == regime]
        spread = sub["spread_10y2y"].dropna()
        chg    = sub["spread_3m_chg"].dropna()
        rows.append({
            "Stress Regime":          regime,
            "Avg Spread (ppts)":      round(spread.mean(), 2) if not spread.empty else "—",
            "Avg 3M Spread Chg":      round(chg.mean(),    2) if not chg.empty    else "—",
            "% Months Inverted":      f"{(spread < 0).sum() / len(spread) * 100:.0f}%" if not spread.empty else "—",
            "n":                      len(spread),
        })
    return pd.DataFrame(rows).set_index("Stress Regime")


def section4_summary(df: pd.DataFrame, vals: dict) -> str:
    """Concise summary block for Section 4."""
    valid = df[df["stress_regime"].isin(STRESS_REGIMES)].copy()
    total = len(valid)
    current_stress = vals.get("stress_regime", "Unknown")
    current_yc     = vals.get("yc_regime",     "Unknown")

    # Which stress regime has the highest inversion frequency (weakest curve structure)
    worst_regime   = None
    worst_inv_pct  = -1.0
    worst_spread   = float("nan")
    for regime in STRESS_REGIMES:
        sub = valid[valid["stress_regime"] == regime]["spread_10y2y"].dropna()
        if not sub.empty:
            inv_pct = (sub < 0).sum() / len(sub) * 100
            if inv_pct > worst_inv_pct:
                worst_inv_pct = inv_pct
                worst_regime  = regime
                worst_spread  = sub.mean()

    # Current regime frequency
    cur_n   = len(valid[valid["stress_regime"] == current_stress]) if current_stress in STRESS_REGIMES else 0
    cur_pct = cur_n / total * 100 if total > 0 else 0

    # High stress inversion rate
    high_inv = ""
    high_sub = valid[valid["stress_regime"] == "High Stress"]["spread_10y2y"].dropna()
    if not high_sub.empty:
        pct_inv = (high_sub < 0).sum() / len(high_sub) * 100
        high_inv = f"In High Stress periods, the curve was inverted {pct_inv:.0f}% of months."

    lines = []
    if worst_regime:
        lines.append(
            f"- Inversion frequency was highest during **{worst_regime}** "
            f"({worst_inv_pct:.0f}% of months), despite a positive average spread ({worst_spread:+.2f} ppts)."
        )
    if high_inv:
        lines.append(f"- {high_inv}")
    lines.append(
        f"- **Current stress regime** (*{current_stress}*): "
        f"{cur_n} of {total} classified months ({cur_pct:.0f}% of history)."
    )

    char_map = {
        ("Normal",        "Low Stress"):      "historically the most stable combination for fixed-income conditions.",
        ("Normal",        "Moderate Stress"): "historically a common environment — near baseline macro conditions.",
        ("Normal",        "High Stress"):     "historically unusual — elevated stress during a normal curve has been relatively rare.",
        ("Flat",          "High Stress"):     "historically associated with late-cycle tightening and compressed term premium.",
        ("Flat",          "Moderate Stress"): "historically associated with transition periods in the rate cycle.",
        ("Inverted",      "High Stress"):     "historically one of the most stressed macro combinations — associated with credit and equity dislocations.",
        ("Inverted",      "Moderate Stress"): "historically observed during late-cycle inversions ahead of policy easing.",
        ("Re-steepening", "High Stress"):     "historically a rare but significant transition — stress coinciding with post-inversion spread widening.",
        ("Re-steepening", "Moderate Stress"): "historically associated with transitional macro dynamics following inversion.",
    }
    key  = (current_yc, current_stress)
    char = char_map.get(key, "historical pattern for this combination is limited.")
    lines.append(f"- **{current_yc} + {current_stress}**: {char}")

    return "  \n".join(lines)

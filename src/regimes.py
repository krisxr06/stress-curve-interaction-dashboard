"""
Regime classification: yield curve and stress.

Yield Curve Regimes (identical to Projects 1 and 2 — same thresholds):
    Priority order (highest first):
    1. Re-steepening  — post-inversion spread widening
    2. Inverted       — spread < 0
    3. Flat           — spread 0 to 0.50
    4. Normal         — spread > 0.50

Stress Regimes:
    Based on combined_stress z-score (see transforms.py):
    - Low Stress      : combined_stress < −0.5
    - Moderate Stress : −0.5 ≤ combined_stress ≤ +0.5
    - High Stress     : combined_stress > +0.5
    - Unknown         : combined_stress is NaN

    IMPORTANT: Stress classification is a simplified rule-based proxy using
    two public market indicators. It is not a risk model and should not be
    used for investment or risk management decisions.
"""

import pandas as pd

# ── Yield Curve ────────────────────────────────────────────────────────────────

YC_REGIMES = ["Inverted", "Re-steepening", "Flat", "Normal"]

YC_COLORS = {
    "Inverted":      "rgba(204,  51,  51, 0.22)",
    "Re-steepening": "rgba(230, 150,  30, 0.22)",
    "Flat":          "rgba(210, 195,  50, 0.22)",
    "Normal":        "rgba( 50, 180,  80, 0.22)",
    "Unknown":       "rgba(150, 150, 150, 0.10)",
}

# ── Stress ─────────────────────────────────────────────────────────────────────

STRESS_REGIMES = ["High Stress", "Moderate Stress", "Low Stress"]

STRESS_COLORS = {
    "High Stress":     "rgba(204,  51,  51, 0.22)",
    "Moderate Stress": "rgba(210, 160,  50, 0.22)",
    "Low Stress":      "rgba( 60, 140, 210, 0.22)",
    "Unknown":         "rgba(150, 150, 150, 0.10)",
}

STRESS_SOLID = {
    "High Stress":     "#dc3333",
    "Moderate Stress": "#d4a030",
    "Low Stress":      "#3c8cd2",
}


# ── Classification functions ──────────────────────────────────────────────────

def classify_yc_regimes(df: pd.DataFrame) -> pd.Series:
    """
    Vectorised YC regime classification — same logic as Projects 1 and 2.
    Applied lowest→highest priority so Re-steepening overwrites lower regimes.
    """
    spread    = df["spread_10y2y"]
    spread_3m = df["spread_3m_chg"]

    had_neg_prior_6m = spread.shift(1).rolling(6, min_periods=1).min() < 0

    cond_re_steep = (
        had_neg_prior_6m
        & (spread_3m > 0.25)
        & (spread >= -0.25)
        & (spread <= 0.75)
    )

    regimes = pd.Series("Unknown", index=df.index, dtype=object)
    regimes[spread > 0.50]                    = "Normal"
    regimes[(spread >= 0) & (spread <= 0.50)] = "Flat"
    regimes[spread < 0]                       = "Inverted"
    regimes[cond_re_steep]                    = "Re-steepening"
    regimes[spread.isna()]                    = "Unknown"

    return regimes.rename("yc_regime")


def classify_stress_regimes(df: pd.DataFrame) -> pd.Series:
    """
    Classify stress regime from combined_stress z-score.

    Thresholds:
        < −0.5  → Low Stress
        −0.5–+0.5 → Moderate Stress
        > +0.5  → High Stress
    """
    score = df["combined_stress"]

    regimes = pd.Series("Unknown", index=df.index, dtype=object)
    regimes[score < -0.5]                      = "Low Stress"
    regimes[(score >= -0.5) & (score <= 0.5)]  = "Moderate Stress"
    regimes[score > 0.5]                       = "High Stress"
    regimes[score.isna()]                      = "Unknown"

    return regimes.rename("stress_regime")


def add_regimes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["yc_regime"]     = classify_yc_regimes(df)
    df["stress_regime"] = classify_stress_regimes(df)
    return df

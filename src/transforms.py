"""
Transformation pipeline for stress × curve interaction analysis.

Derived columns
---------------
spread_10y2y        : DGS10 − DGS2 (ppts)
spread_3m_chg       : 3-month change in spread
baa10y_z            : z-score of BAA10Y over full available history
vix_z               : z-score of VIXCLS over full available history
combined_stress     : mean of available z-scores (see note below)

Stress Score Methodology
------------------------
    z_i = (x_i − mean(x)) / std(x)    over full series history
    combined_stress = mean(available z-scores for that month)

If BAA10Y is available but VIXCLS is not (pre-1990), combined_stress = baa10y_z.
If VIXCLS is available but BAA10Y is not, combined_stress = vix_z.
If neither is available, combined_stress = NaN.

IMPORTANT: This is a simplified descriptive proxy constructed from two public
series. It is not a tradable signal, a risk model output, or investment advice.
See README Methodology section for full disclaimer.

Monthly resampling notes
------------------------
- Most series: month-end last value (consistent with Projects 1 and 2).
- VIXCLS: monthly mean (VIX is a daily volatility measure — averaging is more
  representative than a single month-end observation).
- Short gaps ≤ 3 months are forward-filled; longer gaps preserved as NaN.
"""

import pandas as pd
import numpy as np


def resample_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample to month-end. VIX uses monthly mean; all others use month-end last."""
    non_vix = [c for c in df.columns if c != "VIXCLS"]
    monthly  = df[non_vix].resample("ME").last()

    if "VIXCLS" in df.columns:
        vix_monthly = df["VIXCLS"].resample("ME").mean()
        monthly = monthly.join(vix_monthly)

    monthly = monthly.ffill(limit=3)
    return monthly


def compute_spread(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["spread_10y2y"] = df["DGS10"] - df["DGS2"]
    return df


def compute_3m_changes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["spread_3m_chg"] = df["spread_10y2y"].diff(3)
    return df


def _zscore(series: pd.Series) -> pd.Series:
    """Full-history z-score. NaN values are excluded from mean/std computation."""
    mu  = series.mean(skipna=True)
    sig = series.std(skipna=True)
    if sig == 0 or pd.isna(sig):
        return pd.Series(np.nan, index=series.index)
    return (series - mu) / sig


def compute_stress_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute individual and combined stress z-scores.

    Assumptions (documented):
    - Z-scores are computed over each series' full available history,
      not just the overlap period. This anchors the stress scale to the
      broadest available historical distribution for each component.
    - Combined score = mean of whichever z-scores are non-NaN for that month.
    - Months where no stress component is available yield NaN combined_stress.
    """
    df = df.copy()

    z_cols = []
    if "BAA10Y" in df.columns:
        df["baa10y_z"] = _zscore(df["BAA10Y"])
        z_cols.append("baa10y_z")

    if "VIXCLS" in df.columns:
        df["vix_z"] = _zscore(df["VIXCLS"])
        z_cols.append("vix_z")

    if z_cols:
        df["combined_stress"] = df[z_cols].mean(axis=1)
    else:
        df["combined_stress"] = np.nan

    return df


def apply_transforms(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the full transformation pipeline in order."""
    df = resample_monthly(df)
    df = compute_spread(df)
    df = compute_3m_changes(df)
    df = compute_stress_scores(df)
    return df

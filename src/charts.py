"""
Chart creation module.

Public functions
----------------
stress_by_regime_chart      : avg stress score & components by YC regime
cooccurrence_heatmap        : YC regime × stress regime month-count heatmap
curve_under_stress_chart    : avg spread, spread change, inversion freq by stress regime
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .regimes import YC_REGIMES, STRESS_REGIMES, STRESS_SOLID

_TEMPLATE = "plotly_dark"
_FONT     = "Inter, 'Helvetica Neue', Arial, sans-serif"
_GRID     = "rgba(255,255,255,0.07)"
_ZERO     = "rgba(255,255,255,0.30)"

_YC_SOLID = {
    "Inverted":      "#dc3333",
    "Re-steepening": "#e6962a",
    "Flat":          "#d4c44a",
    "Normal":        "#46b855",
}


# ── Section 2: Stress by YC Regime ────────────────────────────────────────────

def stress_by_regime_chart(df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart: average z-scores (BAA10Y, VIX, combined) per YC regime.
    All values are z-scores so they share a common dimensionless scale.
    """
    valid = df[df["yc_regime"].isin(YC_REGIMES)].copy()

    rows = []
    for regime in YC_REGIMES:
        sub = valid[valid["yc_regime"] == regime]
        rows.append({
            "regime":     regime,
            "avg_baa_z":  sub["baa10y_z"].mean()       if "baa10y_z"       in sub else np.nan,
            "avg_vix_z":  sub["vix_z"].mean()           if "vix_z"          in sub else np.nan,
            "avg_stress": sub["combined_stress"].mean() if "combined_stress" in sub else np.nan,
            "std_stress": sub["combined_stress"].std()  if "combined_stress" in sub else np.nan,
            "n":          sub["combined_stress"].dropna().shape[0],
        })
    stats = pd.DataFrame(rows).set_index("regime")

    fig = go.Figure()

    bar_defs = [
        ("avg_baa_z",  "BAA Spread (z)",   "#f4a460"),
        ("avg_vix_z",  "VIX (z)",          "#c084e8"),
        ("avg_stress", "Combined Stress (z)", "#7EB6FF"),
    ]

    for col, name, color in bar_defs:
        if stats[col].notna().any():
            fig.add_trace(go.Bar(
                name=name,
                x=stats.index,
                y=stats[col].round(2),
                marker_color=color,
                hovertemplate=f"<b>{name}</b><br>%{{x}}: %{{y:.2f}} σ<extra></extra>",
            ))

    # Std dev as error bars on combined stress
    if stats["avg_stress"].notna().any():
        fig.add_trace(go.Scatter(
            x=stats.index,
            y=stats["avg_stress"],
            error_y=dict(type="data", array=stats["std_stress"].tolist(), visible=True,
                         color="rgba(255,255,255,0.4)", thickness=1.5, width=6),
            mode="markers",
            marker=dict(size=0, opacity=0),
            name="±1σ (combined)",
            showlegend=True,
            hoverinfo="skip",
        ))

    fig.add_hline(y=0, line_dash="dot", line_color=_ZERO, line_width=1)

    fig.update_layout(
        template=_TEMPLATE,
        barmode="group",
        title=dict(text="Average Stress Components by Yield Curve Regime (z-scores)", font=dict(size=15)),
        xaxis=dict(title="Yield Curve Regime", showgrid=False),
        yaxis=dict(title="Standard Deviations from Mean (σ)", showgrid=True, gridcolor=_GRID),
        legend=dict(orientation="h", y=-0.20, x=0),
        font=dict(family=_FONT),
        margin=dict(l=70, r=20, t=55, b=90),
        height=420,
    )
    return fig


# ── Section 3: Co-occurrence Heatmap ──────────────────────────────────────────

def cooccurrence_heatmap(df: pd.DataFrame, current_yc: str, current_stress: str) -> go.Figure:
    """
    Heatmap of historical month counts:
        X-axis: Yield Curve Regime
        Y-axis: Stress Regime (High at top)
        Color:  count of months
    Current combination is annotated with ▶.
    """
    valid = df[
        df["yc_regime"].isin(YC_REGIMES) & df["stress_regime"].isin(STRESS_REGIMES)
    ].copy()

    counts = (
        valid.groupby(["stress_regime", "yc_regime"])
        .size()
        .reset_index(name="months")
    )
    pivot = (
        counts.pivot(index="stress_regime", columns="yc_regime", values="months")
        .fillna(0)
        .reindex(index=STRESS_REGIMES, columns=YC_REGIMES, fill_value=0)
    )
    z = pivot.values.astype(int)

    total = z.sum()
    cell_text = []
    for row in z:
        row_text = []
        for v in row:
            pct = v / total * 100 if total > 0 else 0
            row_text.append(f"{int(v)}<br>{pct:.0f}%" if v > 0 else "—")
        cell_text.append(row_text)

    annotations = []
    if current_yc in YC_REGIMES and current_stress in STRESS_REGIMES:
        annotations.append(dict(
            x=current_yc, y=current_stress,
            text="▶ NOW", showarrow=False,
            font=dict(color="white", size=9, family=_FONT),
            xref="x", yref="y", yshift=14,
        ))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=YC_REGIMES,
        y=STRESS_REGIMES,
        text=cell_text,
        texttemplate="%{text}",
        textfont=dict(size=11, family=_FONT),
        colorscale="Blues",
        colorbar=dict(title=dict(text="Months", side="right"), thickness=14, len=0.8),
        hovertemplate=(
            "YC: <b>%{x}</b><br>"
            "Stress: <b>%{y}</b><br>"
            "Months: <b>%{z}</b><extra></extra>"
        ),
        xgap=3, ygap=3,
    ))

    fig.update_layout(
        template=_TEMPLATE,
        title=dict(text="Historical Co-occurrence: Yield Curve × Stress Regime (months / %)", font=dict(size=15)),
        xaxis=dict(title="Yield Curve Regime", tickfont=dict(size=12)),
        yaxis=dict(title="Stress Regime", autorange="reversed", tickfont=dict(size=12)),
        font=dict(family=_FONT),
        margin=dict(l=150, r=60, t=60, b=60),
        height=360,
        annotations=annotations,
    )
    return fig


# ── Section 4: Curve Behavior Under Stress ────────────────────────────────────

def curve_under_stress_chart(df: pd.DataFrame) -> go.Figure:
    """
    Two-panel chart:
        Left  : average 10Y-2Y spread (ppts) by stress regime
        Right : % of months the curve was inverted, by stress regime
    """
    valid = df[df["stress_regime"].isin(STRESS_REGIMES)].copy()

    avg_spread, pct_inv = [], []
    for regime in STRESS_REGIMES:
        sub = valid[valid["stress_regime"] == regime]
        spread_vals = sub["spread_10y2y"].dropna()
        avg_spread.append(spread_vals.mean() if not spread_vals.empty else np.nan)
        pct_inv.append(
            (spread_vals < 0).sum() / len(spread_vals) * 100
            if not spread_vals.empty else np.nan
        )

    colors = [STRESS_SOLID.get(r, "#888") for r in STRESS_REGIMES]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Avg 10Y–2Y Spread (ppts)", "% Months Inverted"),
        horizontal_spacing=0.12,
    )

    fig.add_trace(go.Bar(
        x=STRESS_REGIMES, y=[round(v, 2) if not np.isnan(v) else 0 for v in avg_spread],
        marker_color=colors, name="Avg Spread",
        hovertemplate="%{x}: %{y:+.2f} ppts<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=STRESS_REGIMES, y=[round(v, 1) if not np.isnan(v) else 0 for v in pct_inv],
        marker_color=colors, name="% Inverted",
        hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
    ), row=1, col=2)

    fig.add_hline(y=0, line_dash="dot", line_color=_ZERO, line_width=1, row=1, col=1)

    fig.update_layout(
        template=_TEMPLATE,
        title=dict(text="Yield Curve Structure by Stress Regime", font=dict(size=15)),
        showlegend=False,
        font=dict(family=_FONT),
        margin=dict(l=60, r=40, t=70, b=60),
        height=380,
    )
    fig.update_yaxes(title_text="ppts",   showgrid=True, gridcolor=_GRID, row=1, col=1)
    fig.update_yaxes(title_text="% months", showgrid=True, gridcolor=_GRID, row=1, col=2)
    fig.update_xaxes(showgrid=False)
    return fig

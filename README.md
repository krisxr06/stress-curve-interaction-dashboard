# Stress & Yield Curve Interaction

## Core Question

> *How does market stress interact with yield curve regimes, and what has that historically meant for fixed-income conditions?*

## Why This Project Exists

Yield curve shape and market stress are rarely independent. This project quantifies their historical relationship using public FRED data — examining which curve regimes have coincided with elevated stress, how curve structure behaves conditional on stress state, and where the current environment sits relative to history.

This is the third project in a connected fixed-income research portfolio:
1. `yield-curve-inflation-dashboard` — macro environment: yield curve and inflation regimes
2. `rate-sensitivity-regime-dashboard` — bond duration risk across yield curve regimes
3. `stress-curve-interaction-dashboard` — stress behavior and curve interaction (this project)

## Data Sources

All data from the Federal Reserve Economic Data (FRED):

| Series | Description | Frequency |
|--------|-------------|-----------|
| DGS2 | 2-Year Treasury Constant Maturity | Daily → monthly |
| DGS10 | 10-Year Treasury Constant Maturity | Daily → monthly |
| FEDFUNDS | Effective Federal Funds Rate | Monthly |
| BAA10Y | Moody's Baa corporate spread over 10Y Treasury | Daily → monthly |
| VIXCLS | CBOE VIX daily close | Daily → monthly mean |

BAA10Y coverage begins ~1986. VIXCLS coverage begins January 1990. Analyses using both series are limited to their overlap period (~1990 onwards). All series resampled to month-end; VIX uses monthly mean rather than month-end to better represent realized volatility over the period.

## Methodology

### Yield Change & Spread
- `spread_10y2y` = DGS10 − DGS2
- `spread_3m_chg` = 3-month first difference of spread

### Stress Score — Important Disclaimer

> **This is a simplified descriptive proxy constructed from two public market indicators. It is not a risk model, a tradable signal, or an investment recommendation.**

**Z-score computation:**
```
z_i = (x_i − mean(x)) / std(x)    computed over full available history of each series
```

**Combined stress score:**
```
combined_stress = mean(available z-scores for that month)
```

If only BAA10Y is available (pre-1990), combined_stress = baa10y_z.
If only VIX is available, combined_stress = vix_z.
If neither is available, combined_stress = NaN and the month is classified as Unknown.

Z-scores are anchored to each series' full historical distribution, not just the overlap period. This maximises the historical context for each component.

## Stress Regime Definitions

| Regime | Condition |
|--------|-----------|
| Low Stress | combined_stress < −0.5 |
| Moderate Stress | −0.5 ≤ combined_stress ≤ +0.5 |
| High Stress | combined_stress > +0.5 |

## Yield Curve Regime Definitions

Applied in strict priority order (identical to Projects 1 and 2):

1. **Re-steepening** — spread was negative in prior 6 months AND spread rose > 0.25 ppts over 3 months AND spread is −0.25 to +0.75
2. **Inverted** — spread < 0
3. **Flat** — spread 0 to 0.50
4. **Normal** — spread > 0.50

## Dashboard Walkthrough

| Section | Content |
|---------|---------|
| **1 — Current Snapshot** | 2Y, 10Y, Fed Funds, spread, BAA10Y, VIX, stress score, both regime badges |
| **2 — Stress by Curve Regime** | Avg z-score bar chart + raw values table by YC regime |
| **3 — Stress × Curve Interaction** | Co-occurrence heatmap (centerpiece) + 4 observational bullets |
| **4 — Curve Behavior Under Stress** | Spread and inversion stats by stress regime + summary bullets |

## Key Takeaways

- **Inverted + High Stress** is historically among the least common combinations, but has coincided with significant credit spread and equity dislocations.
- **Normal curve regimes** have historically coincided with Low or Moderate stress the vast majority of the time — High stress during a normal curve has been the exception.
- **Re-steepening** is rare (~4% of months) and has historically occurred during transitional macro environments; its stress profile varies depending on whether it follows a shallow or deep inversion.
- **Stress regimes drive curve structure**: High Stress periods have historically been associated with lower average spreads and higher inversion frequency than Low Stress periods.

## How to Run

```bash
cd stress-curve-interaction-dashboard
pip install -r requirements.txt
streamlit run app.py
```

### Optional: FRED API Key
```bash
cp .env.example .env
# Edit .env: FRED_API_KEY=your_key_here
```
Free API key: <https://fred.stlouisfed.org/docs/api/api_key.html>

Data is cached in `data/processed/` as parquet files on first run (refreshed every 24 hours).

## Disclaimer

This is an educational portfolio project. It is not investment advice. Stress regimes are simplified rule-based classifications using two public market indicators. The combined stress score is a descriptive proxy only — it is not a risk model output and should not be used for investment or risk management decisions. Historical patterns are not predictive of future outcomes.

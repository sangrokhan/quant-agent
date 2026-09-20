# Mass Index (Dorsey) Reversal Bulge — rejected

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_mass_index_reversal_bulge.py`
**Source:** [stockcharts.com ChartSchool — Mass Index](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/mass-index) (browser_exec fallback, web_search DDGS backend TLS-errored); corroborating Google SERP snippets (Investopedia, TradingView, TradingSim, GU Analyser, Definedge Securities — identical mechanical rule across all).

## Hypothesis

Mass Index = 25-period rolling sum of (9-EMA(H-L) / 9-EMA(9-EMA(H-L))).
Dorsey's disclosed "reversal bulge" signal: MI rises above 27, then falls
back below 26.5. Since MI has no directional bias, use the PRIOR trend
(price vs. trend SMA) to set direction: downtrend + reversal bulge =>
bullish reversal (go long); uptrend + reversal bulge => bearish reversal
(go flat).

## Grid test summary (`grid_result_mass_index_reversal_bulge.json`)

- Grid: `bulge_threshold` ∈ {26, 27} × `trend_sma` ∈ {20, 50} × 4 symbols
  (QQQ, SPY, BTC/USDT, ETH/USDT) × 3 vol terciles = 48 cells.
- **pass_fraction: 0.125** (6/48), all 6 passes on equity, 0 on crypto.
- by_vol_regime: low 4/16, mid 2/16, high 0/16.
- Best cell: SPY, bulge_threshold=27/trend_sma=50, low-vol, Sharpe=1.78 —
  but this is a narrow low-vol-slice result.

## Full-sample sweep (2017-2026, QQQ & SPY, bulge_threshold ∈ {24,25,26,27}, trend_sma ∈ {20,50})

Best full-sample: SPY bulge_threshold=27/trend_sma=50, Sharpe=0.869 (MDD
0.227). **No config on either symbol clears the Sharpe≥1.0 accept bar
full-sample** — the grid's low-vol-slice passes do not survive to the full
sample.

## Decision: REJECTED

No full-sample Sharpe pass on any tested config/symbol. The single-config
validator suite (Steps 7) was not run further given this decisive
full-sample failure across the parameter sweep already tried.

## Notes

First Mass Index strategy in this repo — distinct from all other
volatility-regime filters (measures high-low range EXPANSION VELOCITY via
a double-EMA ratio, not realized-vol terciles/ATR/Bollinger width), and
from Bollinger Band strategies (bulge-then-reset pattern, not a threshold
level). Kept as a record; not a near-miss worth revisiting without a
materially different directional overlay than Dorsey's own trend-SMA rule.

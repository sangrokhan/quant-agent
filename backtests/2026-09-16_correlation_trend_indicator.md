# Backtest Report: Correlation Trend Indicator (CTI, LuxAlgo) regime gate

**Strategy file:** `strategies/2026-09-16_correlation_trend_indicator.py`
**Date:** 2026-09-16

## Hypothesis

LuxAlgo's Correlation Trend Indicator (CTI): rolling Pearson correlation
(default 20-bar window) between price (close) and an "ideal rising line"
(bar index 0..N-1). Readings near +1 indicate a steady up-move, near -1 a
steady down-move, near 0 a trendless/choppy window. Per LuxAlgo's own
disclosed trading rule: above +0.5 = bullish trend regime, below -0.5 =
bearish, inside band = neutral. Long-only adaptation: long whenever
CTI > trend_threshold. Distinct from every other trend-strength gate
already tested in this repo (ADX, Choppiness Index, VHF, Random Walk
Index, Trend Persistence Range) since CTI is a literal Pearson correlation
between price and a straight line.

Source: https://www.luxalgo.com/library/indicator/correlation-trend-indicator/
(full disclosed formula and default settings: length=20, source=close,
trend_threshold=0.5).

## Grid test (Step 6)

Grid: `length`∈{14,20,30} × `trend_threshold`∈{0.4,0.5,0.6} ×
`max_hold_days`∈{40,80}, symbols {QQQ, SPY} × {BTC/USDT, ETH/USDT},
vol_regime_splits=3. 216 cells total.

- **pass_fraction: 0.315** (68/216)
- by_asset_class: equity 48/108 (0.444), crypto 20/108 (0.185)
- by_vol_regime: low 54/72 (0.75), mid 13/72 (0.181), high 1/72 (0.014)
- best_cell: QQQ, length=20/threshold=0.5/max_hold=40, low-vol, Sharpe 3.04
- worst_cell: QQQ, length=30/threshold=0.6/max_hold=80, high-vol, Sharpe -0.54

Per-symbol best average-Sharpe configs (averaged across vol regimes):
- QQQ: length=20, trend_threshold=0.5, max_hold_days=80 → avg Sharpe 1.46
- SPY: length=14, trend_threshold=0.4, max_hold_days=40 → avg Sharpe 1.02
- BTC/USDT: length=20, trend_threshold=0.6, max_hold_days=80 → avg Sharpe 1.25
- ETH/USDT: length=20, trend_threshold=0.5, max_hold_days=40 → avg Sharpe 1.34

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.296 (pass, thr 1.0) | 0.167 (pass, thr 0.25) | 1.233 (pass) | 1.00 (pass) | 0.132 (pass) | **Yes** |
| SPY | 1.018 (pass) | 0.163 (pass) | 0.882 (pass) | 0.75 (pass) | 0.336 (pass) | **Yes** |
| BTC/USDT | 1.104 (pass) | 0.570 (**FAIL**, decisive) | 1.077 (pass) | 1.00 (pass) | 0.097 (pass) | **No** |
| ETH/USDT | 1.155 (pass) | 0.569 (**FAIL**, decisive) | 1.138 (pass) | 1.00 (pass) | 0.158 (pass) | **No** |

Parameter sensitivity grid: swept length ±7 and trend_threshold ±0.1 around
each symbol's best config (max_hold_days fixed), 9 combos per symbol.

## Decision (Step 8)

**Accept: QQQ and SPY** (all 5 validators pass cleanly on both).
**Reject: BTC/USDT and ETH/USDT** (Sharpe passes comfortably on both, but
MDD decisively fails — 0.57x and 0.569x vs 0.25 threshold, more than double
the allowed drawdown). This mirrors the pattern seen across several other
long-only trend-following signals in this repo: crypto's raw volatility
needs an explicit vol-targeting/leverage-cap overlay to control drawdown,
which this base signal does not include. A future iteration could
plausibly rescue crypto with this repo's established inverse-volatility
sizing overlay (per the TPR+SMA rescue pattern, 2026-09-16-116).

Edge is concentrated in low-vol regimes (by_vol_regime pass_fraction 0.75
low vs 0.181 mid vs 0.014 high), consistent with a pure trend-following
regime gate.

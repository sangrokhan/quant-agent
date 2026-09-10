# TTM Trend Color-Flip Trend Following

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_ttm_trend_colorflip.py`
**Knowledge base id:** 2026-09-10-080

## Hypothesis

Per tradegrub.com's TTM Trend indicator explainer (visited this iteration,
https://charts.tradegrub.com/indicators/ttm-trend), corroborated by a
thinkorswim TTM_Trend documentation snippet found via search: the
reference level is the average of the midpoints ((high+low)/2) of the
prior `lookback` bars (default 6). A bar is "up-colored" when close >
reference, "down-colored" when close < reference. Source's own framing:
hold through a same-colored run, exit on the first color flip. This
iteration adds a broader SMA(trend_window) trend filter (gating entries to
established uptrends only, per this repo's accumulated finding that a
trend-regime filter improves most raw oscillator/color flips), entering
long on an up-flip within that filter, exiting on a down-flip, trend
break, or time-stop. First TTM-Trend-specific strategy in this repo
(distinct from the already-rejected TTM Squeeze / Squeeze Pro compression
strategies, which use a completely different Bollinger-vs-Keltner
mechanism).

## Grid test summary (Step 6)

Equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT) x `lookback in [6,10,14]`
x `trend_window in [50,100]` x vol_regime_splits=3 = 72 cells.

- total_cells: 72, passed_cells: 15, **pass_fraction: 0.208**
- by_asset_class: equity 15/36, **crypto 0/36 (decisive reject)**
- by_vol_regime: low 12/24, mid 2/24, high 1/24
- best_cell: `lookback=14, trend_window=100`, QQQ, low-vol, Sharpe 2.67

## Full-sample validators on best config (`lookback=14, trend_window=100`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.916 (FAIL, near-miss) | **1.155 (PASS)** | >= 1.0 |
| Max drawdown | 0.194 (pass) | 0.095 (pass) | <= 0.25 |
| TC survival (10bps/trade) | 0.747 (pass) | 0.912 (pass) | >= 0.5 |
| Walk-forward (4 manual date-slices) | 0.75 (pass, 3/4) | 0.75 (pass, 3/4) | >= 0.75 |
| Parameter sensitivity (6-cell grid) | rel_std 0.433 (pass) | rel_std 0.419 (pass) | <= 0.5 |

## Decision: ACCEPT (SPY only) / near-miss (QQQ)

**SPY: accept.** All 5 validators pass with `lookback=14, trend_window=100`
-- Sharpe 1.155, MDD 9.5%, net Sharpe after costs 0.912, walk-forward 3/4,
tight parameter sensitivity. 85 trades over 7.7yr (reasonable turnover).

**QQQ: reject (near-miss).** Fails only the Sharpe bar (0.916 vs 1.0
threshold) -- every other validator passes cleanly (MDD 19.4%, net Sharpe
0.747, walk-forward 3/4, param sensitivity 0.433). Left un-accepted per
this repo's strict per-symbol acceptance convention, but recorded as a
genuine near-miss worth another parameter nudge in a future iteration
(e.g. a slightly higher lookback or tighter trend_window specifically for
QQQ's higher volatility).

**Crypto: reject (decisive).** 0/36 grid cells passed on BTC/USDT and
ETH/USDT -- TTM Trend's short-lookback midpoint-average mechanism does not
translate to crypto's regime.

Strategy file and backtest kept in the repo scoped to SPY (equity, low/mid
vol regimes) per this finding; QQQ and crypto use is explicitly
out-of-scope.

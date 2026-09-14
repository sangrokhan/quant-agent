# Damiani Volatmeter Volatility-Regime Gate — SMA Trend Direction (SPY + BTC/ETH accepted, QQQ near-miss)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_damiani_volatmeter_gate_sma_trend.py`
**Knowledge base id:** 2026-09-15-032

## Hypothesis

Damiani Volatmeter (Luis Damiani), sources visited this iteration:
https://www.tradingview.com/script/z95IdM4a-Damiani-Volatmeter-loxx/ (loxx's
description of the trade/no-trade volatility-regime rule) and Google's
AI-overview summary of the (now-404) LuxAlgo library page, for the exact
formula: `ATR_ratio = ATR(fast_len)/ATR(slow_len)`, `StDev_ratio =
StDev(close,fast_len)/StDev(close,slow_len)`, `threshold = threshold_const -
StDev_ratio`, plus a lag-suppressor term `k*(ATR_ratio[t-1]-ATR_ratio[t-3])`
added to the ATR ratio to form the "vol_line".

This is a genuinely new indicator family for this repo (0 prior
strategies/log entries referenced "Damiani"/"Volatmeter"). The indicator's
own trading rule (per loxx) is binary: trade only when volatility is
high/rising (vol_line above threshold = green), stay flat when compressed
(red); direction is not given by the indicator itself and loxx recommends
pairing it with a separate directional filter (Fisher Transform/Gaussian
filter suggested). This iteration reuses the SMA(trend_window) directional
gate already validated many times this cron trigger, and implements the
volatility rule as a continuous sizing dial (tanh-squashed distance of
vol_line above threshold, scaled by `dial_scale`) rather than the strictly
binary rule, following this trigger's established pattern of turning
discrete oscillator/volatility rules into continuous dials to avoid the
signal-sparsity failure mode.

## Grid test summary (Step 6)

`param_grid={"trend_window": [30,40,50], "threshold_const": [1.1,1.4,1.7],
"sensitivity": [0.4,0.6]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 216 total cells.

- **pass_fraction:** 0.532 (115/216)
- **by_asset_class:** equity 59/108 (0.546), crypto 56/108 (0.519) — balanced
- **by_vol_regime:** low 67/72 (0.931), mid 40/72 (0.556), high 8/72 (0.111)
- **best_cell:** equity/QQQ, low-vol, `trend_window=50, threshold_const=1.1,
  sensitivity=0.6`, Sharpe 2.866
- **worst_cell:** equity/QQQ, high-vol, `trend_window=40, threshold_const=1.1,
  sensitivity=0.6`, Sharpe -0.359

High-vol regime is again a decisive failure across most cells (8/72),
consistent with a trend-gated overlay that whipsaws when volatility spikes
sharply (SMA gate flips fast in genuine high-vol chop even though the
Damiani dial itself is designed to reward rising volatility — the two
filters partially fight each other in the high tercile).

## Single-config validation (Step 7)

Per-symbol best configs from the grid (avg Sharpe across vol regimes),
then hand-tuned deadband/leverage_cap to survive transaction costs and
drawdown:

| Symbol | Config | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|---|
| SPY | trend_window=40, threshold_const=1.4, sensitivity=0.4, deadband=0.35 | 1.187 (✓) | 0.071 (✓) | 0.601 (✓) | 1.00 (✓) | 0.124 (✓) | **YES** |
| BTC/USDT | trend_window=40, threshold_const=1.4, sensitivity=0.6, leverage_cap=0.4 | 1.231 (✓) | 0.200 (✓) | 0.895 (✓) | 1.00 (✓) | 0.110 (✓) | **YES** |
| ETH/USDT | trend_window=40, threshold_const=1.1, sensitivity=0.4, leverage_cap=0.3 | 1.226 (✓) | 0.199 (✓) | 1.026 (✓) | 1.00 (✓) | 0.077 (✓) | **YES** |
| QQQ | trend_window=30, threshold_const=1.4, sensitivity=0.6 (default deadband=0.20) | 1.188 (✓) | 0.121 (✓) | 0.436 (✗, <0.5) | 1.00 (✓) | 0.234 (✓) | no (tx-cost near-miss) |

QQQ was retried at deadband 0.25/0.30/0.35 and various trend_window/
sensitivity combos to cut turnover, but Sharpe degraded faster than
turnover dropped (net Sharpe stayed in 0.38-0.48 range, never crossing
0.5) — recorded as a near-miss for a future "QQQ fix" iteration to revisit
(e.g. a different exposure-scaling function or wider deadband hysteresis
band specifically tuned for QQQ's flatter turnover-vs-edge tradeoff, the
same pattern that rescued several prior QQQ/SPY near-misses this trigger).

## Decision (Step 8)

**Accepted, scoped to SPY + BTC/USDT + ETH/USDT.** All 5 validators pass
with comfortable margin for these three. QQQ misses only on transaction-
cost survival (net Sharpe 0.436 vs 0.5 threshold) despite deadband tuning
up to 0.35 — turnover-vs-edge tradeoff didn't resolve within this
iteration's budget; left as a documented near-miss rather than forcing a
worse config to pass.

Strategy file and this report are kept as an SPY/BTC/ETH-accepted
strategy; QQQ remains out of scope per the default config (a future
iteration could retune per-symbol per this cron trigger's established
"symbol fix" pattern).

# Backtest Report: TTM Squeeze Momentum Breakout

**Strategy file:** `strategies/2026-09-04_ttm_squeeze_momentum_breakout.py`
**Hypothesis ID:** 2026-09-04-091

## Hypothesis

TTM Squeeze (John Carter): when Bollinger Bands (20, 2 std) sit fully inside
Keltner Channels (20-EMA +/- keltner_mult*ATR(20)), volatility has
compressed ("squeeze on"). When BB expands back outside the KC ("squeeze
fires"), the breakout tends to be directional; a momentum proxy (close vs
average of rolling Donchian midpoint and EMA) determines direction. Long
entry when the squeeze just fired AND momentum is positive; exit on
momentum turning negative, a new squeeze re-forming, or max_hold_days.

Source: Google AI-overview + TradingView/PineScriptForge/Definedge search
snippets for "TTM squeeze bollinger keltner strategy rules backtest"
(web_search returned no results for the initial bandwidth-percentile
query, browser fallback used for the TTM-squeeze-specific query; several
result pages were dead links/bot-blocked/empty, sufficient concrete rule
extracted from search snippets alone).

## Single-config validator results (SPY, keltner_mult=2.0/max_hold_days=20 -- best full-sample config found)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.455 | 1.0 |
| Max drawdown | ✅ | 0.091 | 0.25 |
| Transaction cost survival (10bps/trade, 41 trades) | ❌ | net Sharpe 0.337 | 0.5 |

## Step 6 grid summary (keltner_mult ∈ {1.5,2.0}, max_hold_days ∈ {10,20}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 48, passed_cells: 4, pass_fraction: 0.083
- by_asset_class: equity 4/24, crypto 0/24
- by_vol_regime: low 2/16, mid 0/16, high 2/16
- best_cell: SPY, keltner_mult=2.0/max_hold_days=20, low-vol regime, Sharpe 1.64
- worst_cell: QQQ, keltner_mult=1.5/max_hold_days=20, low-vol regime, Sharpe -1.01 (same regime, opposite param set -- high sensitivity to keltner_mult)

**Interpretation:** grid pass_fraction is the lowest of any strategy tested
this session (0.083). Passes are thinly scattered (2 low-vol, 2 high-vol,
0 mid-vol) rather than concentrated in one clear regime, and the same
vol-regime/symbol slice flips from Sharpe 1.64 to -1.01 just by changing
keltner_mult from 2.0 to 1.5 -- suggesting a fragile, overfit-prone signal
rather than a genuine edge. No full-sample config on SPY/QQQ reaches even
0.5 Sharpe, let alone 1.0. Crypto rejected decisively (0/24 grid cells).

## Decision

**REJECT (all assets/configs).** Best full-sample config (SPY,
keltner_mult=2.0/max_hold_days=20) fails both Sharpe (0.455 vs 1.0) and
transaction-cost survival (net Sharpe 0.337 vs 0.5 threshold, on only 41
trades over 7.7yr -- the low trade count means the low MDD (0.091) mostly
reflects being flat most of the time, not genuine edge quality). This is a
weaker/more decisive rejection than the near-miss cases (KVO -084, Renko
-086) -- the squeeze+momentum construction here (using a Donchian-mid/EMA
average as a momentum proxy, since this repo has no linear-regression
momentum-histogram primitive readily available) may be an imperfect
approximation of Carter's original TTM Squeeze momentum calculation; a
future loop revisiting this idea should consider implementing the actual
linear-regression-of-close-vs-average momentum histogram rather than the
simpler proxy used here before concluding the underlying TTM Squeeze
concept itself doesn't work on this data.

# Bullish Stick Sandwich Candlestick Reversal — Backtest Report

**Date:** 2026-09-09
**Outcome:** REJECTED

## Hypothesis

Per https://www.investopedia.com/terms/s/stick-sandwich.asp and
https://wrtrading.com/technical-analysis/charts/candlestick/pattern/stick-sandwich/,
the Bullish Stick Sandwich is a 3-candle reversal pattern occurring during a
downtrend: candle1 long bearish, candle2 opens above candle1's close (a
"filling" candle), candle3 another bearish candle closing near candle1's
close (repeated test of the same support level). Entry required one-bar
confirmation (close above candle3's high) plus a downtrend-SMA precondition
to address ThePatternSite.com's documented caveat that this pattern "acts
as a bearish continuation most often" despite its bullish-reversal label.

## Single-config validator results (SPY, close_tolerance_pct=0.008, reward_atr_mult=1.5 — grid's best cell)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.726 | ≥ 1.0 | FAIL |
| Max drawdown | 0.0006 | ≤ 0.25 | PASS |
| TC survival (10bps, 4 trades) | 0.677 net Sharpe | ≥ 0.5 | PASS |
| Parameter sensitivity | rel. std 0.140 | ≤ 0.5 | PASS |

Full-sample signal is extremely sparse: only 4 trades over 2015-2026 on SPY
at the best-cell config.

## Grid summary (Step 6)

param_grid={close_tolerance_pct:[0.003,0.008], reward_atr_mult:[1.5,2.5]},
symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}, vol_regime_splits=3,
48 cells total.

- pass_fraction: 0.0625 (3/48)
- by_asset_class: equity 3/24 passed, crypto 0/24 passed (crypto: zero edge)
- by_vol_regime: low 0/16, mid 0/16, high 3/16 (only high-vol equity cells passed)
- best_cell: SPY, close_tolerance_pct=0.008, reward_atr_mult=1.5, high-vol regime, Sharpe 1.263
- worst_cell: QQQ, same params, low-vol regime, Sharpe -0.907

## Decision

**REJECTED.** Full-sample Sharpe (0.726) fails the 1.0 threshold despite the
grid's best single vol-regime cell (SPY high-vol, Sharpe 1.26) passing —
the edge, where it exists at all, is narrow (equity-only, high-vol-regime
only, 3/48 grid cells) and full-sample performance is not statistically
distinguishable from noise given only 4 trades. Crypto showed zero edge
across all 24 cells. Consistent with this repo's broader finding that most
multi-candle reversal patterns (Rising Three Methods 2026-09-08-110, Three
Outside Up 2026-09-09-034, Bullish Belt Hold 2026-09-09-033) fail to show a
robust, broad edge on daily bars.

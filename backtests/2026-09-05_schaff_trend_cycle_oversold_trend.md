# Schaff Trend Cycle Oversold-Recovery + Trend Gate — REJECTED

**Strategy file:** `strategies/2026-09-05_schaff_trend_cycle_oversold_trend.py`
**Knowledge base id:** 2026-09-05-088
**Source:** https://quantstrategy.io/blog/understanding-the-schaff-trend-cycle-stc-indicator/

## Hypothesis

STC (MACD 23/50 -> stochastic-of-MACD -> double 3-period SMA smoothing)
crossing above its signal line while recovering from an oversold reading
(<25 within last 5 bars), gated by a trend SMA, would improve on the
already-accepted-narrowly (SPY only) plain centerline-crossover STC
variant (2026-09-04-080) by requiring a genuine oversold-bounce setup
instead of an unconditional centerline cross.

## Grid test summary (96 cells: equity QQQ/SPY + crypto BTC/ETH, params
stoch_window in {10,20} x trend_window in {50,100} x max_hold_days in
{15,20}, vol_regime_splits=3)

- pass_fraction: 0.188 (18/96)
- by_asset_class: equity 18/48, crypto 0/48
- by_vol_regime: low 8/32, mid 10/32, high 0/32
- Naive best_cell: SPY, stoch_window=20, trend_window=50,
  max_hold_days=15, low-vol Sharpe 1.796

## Full-sample re-check (best params per symbol)

| Symbol | Best params | Full-sample Sharpe | Threshold |
|---|---|---|---|
| QQQ | stoch=10, trend=100, hold=15 | 0.586 | 1.0 (FAIL) |
| SPY | stoch=20, trend=100, hold=20 | 0.658 | 1.0 (FAIL) |
| BTC/USDT | stoch=20, trend=100, hold=20 | 0.040 | 1.0 (FAIL) |
| ETH/USDT | stoch=20, trend=100, hold=20 | 0.032 | 1.0 (FAIL) |

## Verdict: REJECTED

Despite a higher raw grid pass_fraction than the last two iterations'
strategies, full-sample re-check on every symbol's own best config
decisively fails the Sharpe threshold (best 0.658 on SPY). The
oversold-recovery gate did not meaningfully improve on the already-tested
centerline-crossover STC variant.

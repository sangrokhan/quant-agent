# Backtest Report: Rubber Band Strategy + min_hold_days Rescue

**Strategy file:** `strategies/2026-09-20_rubber_band_minhold_rescue.py`
**Date:** 2026-09-20
**Source:** QuantifiedStrategies.com,
https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(base Rubber Band entry/exit rule, fully disclosed and already used
unchanged in this repo's prior rejected attempt 2026-09-11-074; the
`min_hold_days` fix is this repo's own established rescue pattern, not
a new external source).

## Hypothesis

Direct fix for prior rejection 2026-09-11-074: the fine-tuned QQQ config
(range_window=3, high_window=7, band_mult=2.0) cleared Sharpe (1.387),
MDD (0.131), and walk-forward (1.0) but decisively failed
transaction-cost survival (net Sharpe 0.451, ~56 trades/year) due to the
immediate "exit as soon as close crosses above yesterday's high" trigger
causing excessive churn. This adds a `min_hold_days` gate (suppresses the
exit signal for the first N days post-entry) -- the same fix pattern
already used successfully in this repo for Klinger Volume Oscillator
(2026-09-04-085), ZLEMA/EMA (2026-09-06-171), and Accelerator Oscillator
(2026-09-06-174).

## Grid test summary (Step 6)

Grid: `range_window` in {3,5} x `high_window` in {5,7} x `band_mult` in
{1.5,2.0} x `min_hold_days` in {2,3}, QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto), vol_regime_splits=3, 2012-01-01 to 2026-09-01.

- **Overall pass_fraction:** 0.396 (76/192)
- **By asset class:** equity 76/96 (0.792, very strong) vs crypto 0/96
  (decisive fail).
- **By vol regime:** low 31/64 (0.484), mid 27/64 (0.422), high 18/64
  (0.281) -- edge present across all three regimes, moderately
  concentrated in low/mid.
- **Best cell:** QQQ range_window=3/high_window=7/band_mult=1.5/
  min_hold_days=3, low-vol, Sharpe 2.620.
- **Worst cell:** BTC/USDT range_window=5/high_window=5/band_mult=2.0/
  min_hold_days=3, low-vol, Sharpe -0.791.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param-sens (band_mult 1.25-2.25) | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | range_window=3, high_window=7, band_mult=2.0, min_hold_days=3 | 1.336 | 0.158 | 1.126 | 1.00 (4/4) | 0.110 | 210 |
| SPY | range_window=3, high_window=5, band_mult=1.5, min_hold_days=3 | 1.171 | 0.227 | 0.839 | 1.00 (4/4) | 0.102 | 283 |

All 5 validators pass cleanly for both QQQ and SPY: the `min_hold_days=3`
gate successfully addresses the prior TC-survival failure (net Sharpe now
0.84-1.13 vs the prior 0.451) while keeping Sharpe/MDD/walk-forward/
parameter-sensitivity solid, at the cost of somewhat higher trade counts
than a typical accepted strategy (210-283 trades over 14.5yr, ~15-20
trades/year) but well within transaction-cost tolerance.

## Decision: ACCEPT (QQQ and SPY)

Both equity symbols pass all 5 validators with strong, stable results.
Crypto decisively rejected (0/96 grid cells pass, worst cell Sharpe
-0.79) -- the band-touch mean-reversion mechanism does not transfer to
24/7 crypto price action, consistent with the parent rejection
2026-09-11-074's own crypto finding (0/36 grid cells).

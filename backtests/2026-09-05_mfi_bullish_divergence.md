# 2026-09-05 — MFI Bullish Divergence (QQQ/SPY, crypto)

## Hypothesis
Per FxOpen's "Money Flow Index Trading Strategies"
(https://fxopen.com/blog/en/money-flow-index-trading-strategies/, "MFI
Divergence" section): a bullish divergence -- price makes a new
`swing_lookback`-bar low while MFI (volume-weighted RSI analog) makes a
HIGHER low over the same swing -- signals weakening selling pressure. Long
entry when MFI subsequently crosses back above `oversold_level` (20/25
tested), stop below the divergence-low price. Exit on MFI crossing back
below the oversold level, or a max_hold_days time-stop.

## Grid test (validation/grid_test.py, run_strategy_grid)
- `param_grid`: swing_lookback in [10,15,20], oversold_level in [20,25]
  (max_hold_days fixed at 15)
- symbols: equity [QQQ, SPY], crypto [BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- 72 total cells, **7 passed (pass_fraction = 0.097)**
- by_asset_class: equity 7/36 passed; **crypto 0/36 passed** (decisive reject)
- by_vol_regime: low 0/24, mid 3/24, high 4/24 -- opposite pattern from most
  prior mean-reversion strategies in this repo (edge concentrated in
  mid/high vol, not low-vol)
- best_cell: swing_lookback=15, oversold_level=25, SPY, mid-vol, Sharpe=1.43
- best config across regimes: SPY swing_lookback=15 or 20 @
  oversold_level=25 (2/3 regimes passed); QQQ 0/3 at every param combo

## Single-config validation (swing_lookback=15, oversold_level=25, max_hold_days=15)

| Metric | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe (full period) | 0.843 (FAIL) | -0.306 (FAIL) | >= 1.0 |
| Max drawdown | 0.063 (PASS) | 0.195 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.830 (PASS) | -0.326 (FAIL) | >= 0.5 |
| Walk-forward (manual 4-split) | 1.0, but only 4 trades total (PASS, low signal count) | 0.75 (PASS) | >= 0.75 |

Walk-forward note: manual 4-contiguous-chunk date split used (vbt splitter
bug, as with other recent entries).

## Decision: REJECTED
SPY's best full-sample config (swing_lookback=15, oversold_level=25) fails
the Sharpe >= 1.0 threshold (0.843) despite passing every other validator,
and generates only 4 trades over the ~7.7-year sample -- too few to trust
even if it had passed. QQQ fails decisively (negative Sharpe, negative net
Sharpe after costs). Crypto rejected decisively (0/36 grid cells). The
divergence-detection logic (comparing MFI's rolling low at two swing
occurrences `swing_lookback` bars apart) produces sparse, low-frequency
signals that don't clear the bar with enough statistical weight.

## Notes for future iterations
Unlike most prior mean-reversion strategies in this repo (which concentrate
their edge in low-vol regimes), this divergence detector's pass_fraction
was higher in mid/high-vol regimes (3/24, 4/24) than low-vol (0/24) --
plausibly because divergences require enough price swing amplitude to be
detected at all, which low-vol periods lack. If revisited, consider gating
entries to only mid/high-vol regimes explicitly, and loosening the
divergence-recency window to generate more trades before re-testing.

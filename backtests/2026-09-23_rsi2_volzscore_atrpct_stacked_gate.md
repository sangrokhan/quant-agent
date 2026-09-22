# RSI(2) Mean Reversion + Stacked Volume Z-Score / ATR% Low-Vol Gate (QQQ)

**Date:** 2026-09-23
**Strategy file:** `strategies/2026-09-23_rsi2_volzscore_atrpct_stacked_gate.py`
**KB id:** 2026-09-23-045 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Per Ali Casey's StatOasis 15,552-backtest sweep of 80 volume/volatility
filters on Larry Connors' RSI(2)
(https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter),
the study's own reliable-stacked-pair table (>=15% signal coverage AND
>=50% of variants clearing the 50-trade reliability floor) surfaces
"Volume z-score above 1 + ATR% below its 100-day median" as the best
qualifying stacked pair: 30.1% signals kept, profit factor 2.46 vs 1.70
unfiltered (+0.76), improved profit factor in 97.6% of 96 matched
pairings, drawdown -5.3pp. The single-filter version of the ATR% gate
alone is already accepted SPY-only in this repo (2026-09-20-140, QQQ
Sharpe 0.786 near-miss). This iteration adds the volume z-score condition
on top to see whether it rescues QQQ or extends the accepted scope.

## Grid test (Step 6)

96 cells: `entry_threshold`[5,10] x `exit_threshold`[60,70] x
`vol_z_threshold`[0.5,1.0] x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol regimes
(2019-01-01 to 2026-09-01).

- **pass_fraction:** 0.208 (20/96)
- **by_asset_class:** equity 20/48, crypto 0/48 (decisive fail)
- **by_vol_regime:** low 16/32, mid 0/32, high 4/32
- **best_cell:** entry_threshold=5, exit_threshold=60, vol_z_threshold=1.0,
  QQQ, low-vol, Sharpe=2.316
- **worst_cell:** entry_threshold=10, exit_threshold=60,
  vol_z_threshold=1.0, BTC/USDT, mid-vol, Sharpe=-0.746

## Single-config validation (Step 7) -- best config: entry_threshold=5,
exit_threshold=60, vol_z_threshold=1.0, atr_window=14, atr_lookback=100,
vol_window=50, trend_window=200, max_hold_days=10

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | 1.032 (pass, thr 1.0) | 0.687 (**fail**) |
| Max Drawdown | 5.80% (pass, thr 25%) | 5.58% (pass) |
| Net Sharpe after 10bps costs | 0.883 (pass, thr 0.5) | 0.554 (pass) |
| Walk-forward pass fraction (4-split, manual -- vbt RangeSplitter broken in this env) | 1.0 (pass, thr 0.75) | 0.667 (**fail**) |
| Parameter sensitivity (relative std, 9-combo local sweep) | 0.037 (pass, thr 0.5) | 0.062 (pass) |
| num_trades | 21 | 26 |

## Decision

**Accept QQQ only.** All 5 validators pass for QQQ with a notably tight
5.80% max drawdown and very low parameter sensitivity. SPY fails Sharpe
(0.687 < 1.0) and walk-forward (0.667 < 0.75) -- reject SPY. Crypto
decisively rejected in the grid (0/48). This flips the scope from
2026-09-20-140 (single ATR%-only filter: SPY accepted, QQQ near-miss) --
adding the volume z-score condition on top swaps which symbol clears the
bar, consistent with the source's own finding that stacking mostly
narrows/reshuffles the sample rather than reliably compounding edge in
one fixed direction.

## Source

https://statoasis.com/overfit/research/boost-your-rsi2-strategy-for-sp500-by-48-with-this-volume-filter

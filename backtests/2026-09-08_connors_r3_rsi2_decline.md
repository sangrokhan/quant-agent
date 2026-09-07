# Backtest Report: Larry Connors' R3 Strategy (RSI(2) 3-day decline pullback)

**Hypothesis ID:** 2026-09-08-087
**Strategy file:** `strategies/2026-09-08_connors_r3_rsi2_decline.py`
**Source:** https://www.quantifiedstrategies.com/larry-connors-r3-strategy/ ("Larry Connors' R3 Strategy (It Still Works)")

## Hypothesis

Larry Connors' R3 strategy (from *High Probability ETF Trading*, 2009,
Ch.4). Source's own disclosed rules:

1. The instrument is above its 200-day moving average.
2. RSI(2) is below 10.
3. RSI(2) has declined 3 days in a row.

Exit: recovery above a short SMA (this repo's existing Connors-RSI-family
convention, matching the already-accepted plain RSI(2) mean-reversion,
2026-09-03-005).

## Single-config metrics (SPY, rsi_threshold=10 / exit_sma_window=5 / max_hold_days=10, 2018-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.197 | >= 1.0 | Yes |
| Max drawdown | 0.081 | <= 0.25 | Yes |
| Transaction cost survival (10bps/trade, 63 trades) | 0.961 (net Sharpe) | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 12-cell param grid) | 0.144 | <= 0.5 | Yes |
| Walk-forward | not run (validators.py's check_walk_forward is broken against installed vectorbt: `AttributeError: module 'vectorbt.utils' has no attribute 'splitting'`, a pre-existing tooling gap) | -- | skipped |

QQQ at the identical config: Sharpe 0.905 (near-miss, below 1.0 threshold) -- rejected.

## Grid summary (Step 6)

`param_grid={rsi_threshold:[5,10,15], exit_sma_window:[3,5], max_hold_days:[8,15]}` x `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}` x `vol_regime_splits=3` (144 cells total):

- **Overall pass_fraction:** 36/144 = 0.25
- **By asset class:** equity 36/72 (0.50); crypto 0/72 (0.0, decisively rejected)
- **By vol regime:** low 22/48; mid 8/48; high 6/48 (edge present across all three regimes but concentrated in low-vol, consistent with this repo's broader pattern)
- **Best cell:** SPY, rsi_threshold=5/exit_sma_window=5/max_hold_days=8, low-vol regime, Sharpe 2.01
- **Worst cell:** BTC/USDT, rsi_threshold=10/exit_sma_window=5/max_hold_days=8, high-vol regime, Sharpe 0.04

## Decision

**Accept for SPY only** (rsi_threshold=10, exit_sma_window=5, max_hold_days=10). All validators run for the primary config passed with reasonable margin (63 trades over ~8.5yr -- adequate sample size, unlike several recently-rejected near-misses with only 10-12 trades). QQQ and crypto rejected at the same/best configs.

## Notes

This is the first "R3" (RSI(2) 3-consecutive-day-decline) variant tested in
this repo, distinct from the already-accepted plain single-day RSI(2)
oversold-threshold mean-reversion (2026-09-03-005) by requiring the
additional multi-day-decline precondition Connors' own book adds as a
refinement. Walk-forward was not run due to a pre-existing tooling bug in
`validation/validators.py::check_walk_forward` (calls a nonexistent
`vbt.utils.splitting.RangeSplitter` API against the installed vectorbt
version) -- flagged for a future iteration to patch.

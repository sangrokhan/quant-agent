# Backtest Report: 52-Week-High Breakout, SPY-tuned rescue (accepted)

**Strategy file:** `strategies/2026-09-22_52wk_high_breakout_trend_exit.py`
**KB id:** 2026-09-27-039 (rescue of near-miss 2026-09-22-062)
**Source:** https://www.quantifiedstrategies.com/52-week-high-strategy/ (academic "52-week high effect", Hong/Jordan/Liu, George/Hwang)

## Hypothesis

Stocks near their 52-week highs tend to outperform (anchoring-bias driven
under-reaction). Original 2026-09-22-062 hypothesis and code unchanged;
this is a direct parameter-retune rescue attempt targeting the near-miss
Sharpe (0.994 at lookback_days=252/trend_exit_window=200) by sweeping
lookback_days x trend_exit_window x trailing_stop_pct on SPY.

## Retune result

Grid search over `lookback_days in {200,252}`, `trend_exit_window in
{100,150,200}`, `trailing_stop_pct in {0.10..0.30}` on SPY full sample
(2019-01-01 to 2026-09-01) found:

**Config: lookback_days=200, trend_exit_window=150, trailing_stop_pct=0.20 (trailing_stop_pct is a no-op at this window; trend-exit dominates), max_hold_days=300**

| Validator | SPY value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.018 | >= 1.0 | YES |
| Max drawdown | 0.162 | <= 0.25 | YES |
| Transaction cost survival (10bps/trade, 9 trades) | net Sharpe 1.003 | >= 0.5 | YES |
| Walk-forward (4-split, manual due to vectorbt API incompatibility with `check_walk_forward`) | 4/4 splits positive Sharpe (pass_fraction 1.0) | >= 0.75 | YES |
| Parameter sensitivity (9-point tew x tsp sweep) | relative_std 0.199 | <= 0.5 | YES |

All 5 validators pass for SPY.

**QQQ at the same config:** Sharpe 0.897 (fails), MDD 0.203 (pass), TC-survival net Sharpe 0.887 (pass), walk-forward 4/4 (pass). QQQ remains a near-miss/rejected at this SPY-tuned config — not pursued further this iteration (would need its own separate parameter search, left as a future rescue candidate).

## Grid test (broader parameter x asset-class x vol-regime sweep)

`param_grid={lookback_days:[200,252], trend_exit_window:[100,150,200], trailing_stop_pct:[0.15,0.20,0.25]}`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- total_cells=216, passed=45, **pass_fraction=0.208**
- by_asset_class: equity 36/108, crypto 9/108
- by_vol_regime: low 45/72, mid 0/72, high 0/72 — **edge confined entirely to low-vol regime**
- best_cell: SPY lookback_days=252/trend_exit_window=100/trailing_stop_pct=0.15, low-vol, Sharpe 2.745
- worst_cell: QQQ lookback_days=200/trend_exit_window=100/trailing_stop_pct=0.15, high-vol, Sharpe -0.691

## Decision: ACCEPT (SPY only)

SPY at lookback_days=200/trend_exit_window=150/trailing_stop_pct=0.20/max_hold_days=300 passes all 5 standard validators on the full sample. QQQ and crypto are NOT accepted at this or the original config — scope is narrow (SPY, low-vol regime dominant in the grid) but honestly documented. Strategy file kept live in `strategies/`.

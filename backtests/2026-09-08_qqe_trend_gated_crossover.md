# Backtest Report: QQE Trend-Gated Crossover (2026-09-08)

## Hypothesis
The QQE (Quantitative Qualitative Estimation) indicator's smoothed-RSI line
crossing above its ATR-of-RSI slow trailing band, while all three QQE
component lines sit below the 50-level, signals a bullish momentum shift.
Confirmed with a 100-period EMA trend filter (long only when price above
EMA). Per howtotrade.com's QQE trading-strategy tutorial
(https://howtotrade.com/indicators/qqe-indicator/).

Source: https://howtotrade.com/indicators/qqe-indicator/ (visited 2026-09-08,
via browser_exec fallback after web_search backend failure).

## Strategy file
`strategies/2026-09-08_qqe_trend_gated_crossover.py`

## Grid test summary (Step 6)
Grid: `smooth_period` in [3,5,8] x `max_hold_days` in [10,15,20], equity
(QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), vol_regime_splits=3. 108 total
cells.

- pass_fraction: 0.0648 (7/108)
- by_asset_class: equity 7/54 passed, crypto 0/54 passed (decisive failure)
- by_vol_regime: low 0/36, mid 3/36, high 4/36
- best_cell: smooth_period=5, max_hold_days=10, QQQ, mid-vol, Sharpe=1.70
- worst_cell: smooth_period=3, max_hold_days=15, QQQ, low-vol, Sharpe=-0.71

## Single-config validation (best config: smooth_period=5, max_hold_days=10)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | 1.011 (pass, thresh 1.0) | 0.035 (pass) | 0.944 (pass) | 0.75 (pass) | 0.875 (FAIL, thresh 0.5) |
| SPY | 0.247 (FAIL) | 0.092 (pass) | 0.179 (FAIL) | 0.50 (FAIL) | 0.656 (FAIL) |

## Decision: REJECTED

Even on the single best-performing cell (QQQ), the strategy fails
parameter-sensitivity (relative std 0.875 >> 0.5 threshold) -- returns are
fragile to small changes in `smooth_period`/`max_hold_days`, suggesting the
QQQ Sharpe>1 result is a narrow overfit rather than a robust edge. SPY fails
outright on Sharpe, transaction-cost survival, and walk-forward. Crypto
fails decisively across all 54 cells. Grid pass_fraction of 6.5% is one of
the weakest recorded this cron trigger, concentrated almost entirely in
QQQ mid/high-vol cells.

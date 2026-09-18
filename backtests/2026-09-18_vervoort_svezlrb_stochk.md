# Backtest Report: Vervoort SVEZLRBPercB + Smoothed StochK

**Strategy file:** strategies/2026-09-18_vervoort_svezlrb_stochk.py
**Hypothesis:** Sylvain Vervoort's zero-lag Rainbow-smoothed %b oscillator
(SVEZLRBPercB, TASC Sept 2013 "Oscillators, Smoothed") + companion smoothed
Stochastic %K. Source's own demo strategy: buy when StochK crosses above
oversold territory, sell when it leaves overbought territory. Added this
repo's standard SMA(trend_window) uptrend gate + max_hold_days time-stop
since the raw StochK crossover is not itself trend-aware.

Source: https://traders.com/Documentation/FEEDbk_docs/2013/09/TradersTips.html
(read via browser_exec after web_search DDGS backend failed with repeated
TLS connection errors this iteration).

## Grid summary (Step 6)

144 cells: oversold in {20,30} x trend_window in {100,150,200} x
max_hold_days in {15,30} x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol regimes
(low/mid/high realized-vol terciles).

- Overall pass_fraction: 19/144 = 13.2%
- by_asset_class: equity 12/72 (16.7%), crypto 7/72 (9.7%)
- by_vol_regime: low 11/48 (22.9%), mid 6/48 (12.5%), high 2/48 (4.2%)
- Best cell (single tercile): QQQ, oversold=30/trend_window=150/max_hold_days=15,
  mid-vol Sharpe 2.16
- Best average-Sharpe config across all 3 terciles: QQQ,
  oversold=30/trend_window=200/max_hold_days=30, 3/3 tercile cells pass,
  avg Sharpe 1.386

## Full-sample single-config validation (Step 7)

Config: oversold=30, overbought=70, trend_window=200, max_hold_days=30
(the grid's best average-Sharpe QQQ config, tested full-sample on all 4
symbols).

| Symbol | Sharpe | MDD | TC-net-Sharpe | Walk-fwd | Param-sens (rel std) | All pass |
|---|---|---|---|---|---|---|
| QQQ | 1.315 (pass) | 0.080 (pass) | 1.234 (pass) | 0.50 (fail, thresh 0.75) | 0.845 (fail, thresh 0.5) | **FAIL** |
| SPY | 0.571 (fail) | 0.084 (pass) | 0.486 (fail) | 0.75 (pass) | 0.789 (fail) | **FAIL** |
| BTC/USDT | 0.003 (fail) | 0.544 (fail) | -0.059 (fail) | 0.50 (fail) | 1.492 (fail) | **FAIL** |
| ETH/USDT | 0.044 (fail) | 0.441 (fail) | -0.028 (fail) | 0.75 (pass) | 1.077 (fail) | **FAIL** |

## Outcome: REJECTED (all symbols)

QQQ has the strongest full-sample profile (Sharpe/MDD/TC-survival all
comfortably pass) but fails walk-forward robustness (only 2/4 splits
positive) and decisively fails parameter sensitivity (0.845 vs 0.5
threshold -- swapping trend_window/oversold to {150,20} pairs collapses
performance in at least one combination). SPY marginal on everything.
Crypto (BTC/ETH) decisively rejected: high trade counts (644/662) with the
StochK crossover firing far more often on crypto's characteristic
volatility, combined with catastrophic MDD (0.44-0.54, more than double
threshold) — the max_hold_days=30 time-stop does not adequately contain
drawdown at crypto's volatility scale, unlike equity.

QQQ's isolated grid strength (13.2% overall pass_fraction, concentrated in
low-vol equity cells) does not survive full-sample walk-forward or
parameter-sensitivity scrutiny — a case of grid over-selection on a narrow
best cell rather than a genuinely robust edge.

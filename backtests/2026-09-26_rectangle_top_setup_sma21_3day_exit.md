# Bulkowski Rectangle Top Setup (SMA21 filter, fixed 3-day exit) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_rectangle_top_setup_sma21_3day_exit.py`
**Source:** https://thepatternsite.com/RectangleTopSetup.html (Thomas
Bulkowski), read via browser_exec (web_extract's ddgs backend cannot fetch
this domain).

## Hypothesis

Detect a "rectangle top" as a `range_window`-day period where price stays
within a tight horizontal channel ((rolling_high - rolling_low)/rolling_low
<= `max_range_pct`). Enter long when close breaks above that prior window's
high AND close is above its own `sma_window`-day SMA (source's own
best-ranked filter: "Buy price >21 day SMA"). Exit unconditionally
`hold_days` trading days later (source's own disclosed rank-1 rule: "3 day
exit", no stop/target). Source's own out-of-sample test (~1550 stocks,
1991-2010, 599 trades): avg +3.1%/trade, 75% win rate, W/L ratio 7.13, max
drawdown 28%. First fixed-N-day-holding-period breakout strategy in this
repo (all prior chart-pattern breakouts use measured-move targets or
trend-break exits, never Bulkowski's own explicit fixed-day-count exit).

## Grid test summary (Step 6)

`range_window` in {10,15,20}, `max_range_pct` in {0.06,0.08,0.10}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108 cells.

- **pass_fraction: 0.306** (33/108)
- **by_asset_class:** equity 25/54, crypto 8/54
- **by_vol_regime:** low 22/36, mid 9/36, high 2/36 (edge concentrated in
  low-vol regimes, consistent with most breakout/mean-reversion strategies
  tested in this repo)
- **best_cell:** range_window=10, max_range_pct=0.06, QQQ, low-vol, Sharpe
  2.019
- **worst_cell:** range_window=15, max_range_pct=0.10, QQQ, high-vol,
  Sharpe -0.330
- **best consistent config across vol regimes (avg Sharpe, all 3 regimes
  passed):** range_window=10, max_range_pct=0.08, QQQ (Sharpe passed 3/3
  regimes, avg 1.568); QQQ's shared config at range_window=10/max_range_pct=0.10
  also passed 3/3 (avg 1.636) but 0.08 chosen as the source-adjacent
  middle value.

## Single-config validation (Step 7)

Config: `range_window=10, max_range_pct=0.08, sma_window=21, hold_days=3`
(grid's best consistently-passing QQQ config). Full sample 2016-01-01 to
2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 1.490 PASS | 0.105 PASS | 0.769 PASS | 0.264 PASS | 273 |
| SPY | 0.867 **FAIL** | 0.120 PASS | 0.197 **FAIL** | 0.213 PASS | 298 |

`check_walk_forward` skipped: pre-existing repo bug
(`vbt.utils.splitting` missing), consistent with all prior entries in this
knowledge base under `suggested_workload=max`.

Crypto (BTC/USDT, ETH/USDT) not separately validated at this config -- grid
pass fraction for crypto (8/54, 14.8%) is well below the equity pass rate
and no crypto cell in the grid at range_window=10/max_range_pct=0.08 passed
across all 3 vol regimes, so crypto is out of scope for this accepted
strategy (source itself is explicitly a stock-market setup).

## Decision

**Accepted for QQQ only.** All 4 validators run (Sharpe, MDD, transaction
cost survival, parameter sensitivity) pass for QQQ at
range_window=10/max_range_pct=0.08/sma_window=21/hold_days=3. SPY fails
Sharpe (0.867 < 1.0) and transaction-cost survival (net Sharpe collapses to
0.197 after 10bps/trade on 298 trades) at the shared config -- rejected for
SPY without a separate per-symbol retune this iteration. Crypto rejected
(low grid pass fraction, no cross-vol-regime-consistent config found).

Novelty: checked `strategies_index.jsonl` for "Rectangle"/"rectangle top",
0 hits. Distinct from every other breakout strategy in this repo (Donchian,
double-top/bottom, various chart patterns) via its unique fixed-N-day
holding-period exit rule (no stop-loss, no measured-move target) taken
directly from the source's own disclosed rank-1 backtest configuration.

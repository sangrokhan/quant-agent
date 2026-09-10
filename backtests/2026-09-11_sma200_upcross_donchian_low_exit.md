# 2026-09-11 SMA200 Upcross Entry + SMA200-downcross/Donchian-Low Trailing Exit

## Hypothesis
Per SetupAlpha's "I Tested 56 Trailing Stops on 105,708 Trades" (Aug 9
2026, https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested,
visited this iteration): source's isolated-exit-testing design uses entry
`C > ma200 and C[1] <= ma200[1]` (SMA200 upcross event) with baseline exit
`C < ma200`, layering trailing stops beneath. Source's disclosed #6-of-8
finding: rolling N-day-LOW trailing stop (anchored 1 day back) beats the
close-only channel version by ~+0.24%/trade. Adapted here: entry on
SMA200 upcross EVENT (not continuous close>SMA condition, distinguishing
from every other trend-filtered strategy in this repo), exit whichever
fires first of (SMA200 downcross) or (Donchian N-day-low breach).

Source: https://setup4alpha.substack.com/p/trailing-stop-vs-fixed-stop-tested (visited this iteration)

## Grid summary (run_strategy_grid, param_grid={trend_sma_window:[150,200,250], donchian_low_window:[10,20,30]}, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3)

- total_cells: 108, passed_cells: 29, pass_fraction: 0.269
- by_asset_class: equity 29/54, crypto 0/54
- by_vol_regime: low 18/36, mid 11/36, high 0/36
- best_cell: SPY, trend_sma_window=250, donchian_low_window=20, low-vol regime, Sharpe 2.37

## Single-config validation (full sample)

| Config | Symbol | Sharpe | MDD | TC-adj Sharpe (10bps) | Trades |
|---|---|---|---|---|---|
| sma=200, don=20 | QQQ | 0.779 | 0.321 | 0.596 | 361 |
| sma=250, don=20 (grid best) | QQQ | 0.855 | 0.268 | 0.657 | 373 |
| sma=150, don=10 | QQQ | 0.662 | 0.491 | 0.390 | 559 |
| sma=200, don=20 | SPY | 0.632 | 0.215 | 0.388 | 367 |
| sma=250, don=20 (grid best) | SPY | 0.650 | 0.188 | 0.405 | 373 |
| sma=150, don=10 | SPY | 0.477 | 0.241 | 0.146 | 586 |

## Decision: REJECT

Full-sample Sharpe (0.48-0.86) fails the >=1.0 threshold across every
tested configuration. MDD also fails on most QQQ configs (0.27-0.49 >
0.25) though SPY's best config (0.188) passes. Trade count is high
(361-586 trades) because SMA200 upcross events themselves fire frequently
during choppy/ranging periods around the 200-day average, and the
Donchian-low exit adds further whipsaw churn on top -- consistent with
this repo's broad prior finding that discrete SMA-crossover-EVENT entries
(vs continuous "close>SMA" trend filters) tend to overtrade. Confirms
the source's own framing that this exit-testing methodology measures
"what a trailing stop adds to an exit you already have" rather than a
standalone tradeable edge -- the disclosed marginal improvement from a
better trailing stop (close vs low channel) doesn't translate into an
absolute Sharpe edge once the SMA200-crossover entry mechanic itself is
adopted verbatim in this repo's single-asset long/flat framework. Crypto
rejected decisively (0/54).

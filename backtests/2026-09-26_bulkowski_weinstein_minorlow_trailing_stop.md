# Bulkowski's "Trading Weinstein" Stage-2 Setup (minor-low trailing stop) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_bulkowski_weinstein_minorlow_trailing_stop.py`
**Source:** https://thepatternsite.com/TradingWeinstein.html (Thomas
Bulkowski's own detailed test of Stan Weinstein's Stage-2 method), read
via browser_exec (web_extract's ddgs backend cannot fetch this domain).

## Hypothesis

Entry on breakout above a rolling resistance window while close > SMA(150)
(30-week SMA proxy) with a rising slope. Stop management uses the nearest
confirmed minor swing low (not a fixed distance), only ratcheting up. A
"wait for profit" exit rule sells at the next bar once price closes above
the entry price with today's low also above entry -- Bulkowski's own
disclosed trade-off: sacrifices average gain for a higher win/loss ratio.
This is distinct from all 3 prior Weinstein-family entries in this repo
(2026-09-10-127, -128, 2026-09-18-124), none of which use this specific
minor-low-anchored trailing stop + wait-for-profit exit mechanic.
Bulkowski's own stats: avg gain 6%/5% in/out-of-sample, win/loss ratio
74-75%, max loss -20%/-22%, 448/330 trades.

## Grid test summary (Step 6)

`resistance_window` in {30,50,70}, `pivot_window` in {3,5,7}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108 cells.

- **pass_fraction: 0.361** (39/108) -- the highest grid pass fraction of
  any strategy tested this cron trigger
- **by_asset_class:** equity 22/54, crypto 17/54 (crypto notably strong
  for this repo -- ETH/USDT in particular shows a genuine multi-regime
  edge in the grid, unusual among this repo's tested strategies)
- **by_vol_regime:** low 27/36, mid 12/36, high 0/36
- **best_cell:** resistance_window=50, pivot_window=7, SPY, low-vol,
  Sharpe 2.154
- **worst_cell:** resistance_window=70, pivot_window=7, SPY, high-vol,
  Sharpe -1.240
- **best shared configs:** QQQ at resistance_window=30/pivot_window=3
  (avg 0.902, 2/3 passed); ETH/USDT at resistance_window=70/pivot_window=3
  (avg 0.980, 2/3 passed)

## Single-config validation (Step 7)

Config QQQ: `resistance_window=30, sma_window=150, slope_lookback=10,
pivot_window=3` (an additional local search around this region did not
find anything better -- 0.872 is the ceiling found). Config ETH/USDT:
`resistance_window=70, pivot_window=3`. Full sample 2016-01-01 to
2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 0.872 **FAIL** | 0.118 PASS | 0.611 PASS | 0.236 PASS | 122 |
| ETH/USDT | 0.001 **FAIL** (decisive) | 0.538 **FAIL** | -0.045 **FAIL** | 0.088 PASS | 762 |

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing).

The grid's promising ETH/USDT vol-regime-tercile Sharpes (avg 0.980) did
NOT survive full-sample validation -- 762 trades over 10.5 years (roughly
2 trades/week) is a massive overtrading rate that erodes any edge once
transaction costs and the full unsegmented drawdown path are accounted
for (net Sharpe after 10bps costs actually goes NEGATIVE). This is a
cautionary case for why the grid's tercile-sliced Sharpes alone are
insufficient -- the full-sample single-config validators exist precisely
to catch this kind of overtrading-driven mirage.

## Decision

**Rejected (all symbols).** QQQ is a genuine near-miss (0.872, an
additional local parameter search around the grid's best region did not
clear the bar) but passes every other validator; ETH/USDT looked
promising in the grid but collapses decisively at full-sample validation
due to extreme overtrading (762 trades, net Sharpe goes negative after
costs). Not accepted for either symbol. Flagging QQQ as a recorded
near-miss for a future iteration that wants to try widening the
`sma_window`/`slope_lookback` search further, or adding a minimum-hold /
cooldown rule to reduce ETH/USDT's trade frequency specifically.

Novelty: checked `strategies_index.jsonl` for "Weinstein" -- found 3 prior
entries (2026-09-10-127/128, 2026-09-18-124), all using a simpler
SMA-break/SMA-slope exit. This entry's minor-low-anchored trailing stop +
wait-for-profit exit is a materially different, previously-untested
mechanic taken directly from Bulkowski's own more detailed rule
walkthrough -- confirmed non-duplicate.

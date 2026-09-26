# Bulkowski/Bierovic Ascending Triangle Setup (staged trailing stop) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_bierovic_ascending_triangle_staged_trailing_stop.py`
**Source:** https://thepatternsite.com/BierovicSetup.html (Thomas
Bulkowski, discussing Thomas Bierovic's Sept 2002 Active Trader article),
read via browser_exec (web_extract's ddgs backend cannot fetch this
domain).

## Hypothesis

Detect a flat-top/rising-support ascending triangle over `pattern_window`
days. Enter long on breakout above the flat top, optionally gated by
close > EMA(13) AND close > EMA(55) (source's own entry filter). Exit via
a staged trailing stop: initial stop at pre-breakout low -> breakeven once
gain reaches 50% of triangle height -> trail below prior bar's low once
gain reaches 100% of triangle height. Source's own 1991-2011 test (627
stocks, 1061 triangles): avg gain 0.8%/trade with all filters applied, but
1.7%/trade for the trades the filters EXCLUDED -- source's own conclusion:
"the entry rules do more harm than good." This iteration tests both the
WITH-filter and WITHOUT-filter (`require_ema_filter`) variants directly,
operationalizing the source's own finding as a testable parameter.

## Grid test summary (Step 6)

`flat_top_tol` in {0.02,0.03,0.05}, `require_ema_filter` in {True,False},
equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 72
cells.

- **pass_fraction: 0.25** (18/72)
- **by_asset_class:** equity 12/36, crypto 6/36
- **by_vol_regime:** low 12/24, mid 6/24, high 0/24
- **best_cell:** flat_top_tol=0.05, require_ema_filter=True, SPY, low-vol,
  Sharpe 1.910
- **worst_cell:** flat_top_tol=0.02, require_ema_filter=True, ETH/USDT,
  high-vol, Sharpe -1.196
- **best shared config across QQQ/SPY (avg Sharpe):** flat_top_tol=0.05,
  require_ema_filter=False (QQQ avg 0.614; SPY avg 1.021) -- consistent
  with source's own finding that dropping the EMA filter modestly helps.

## Single-config validation (Step 7)

Config: `pattern_window=15, flat_top_tol=0.05, min_rise_pct=0.03,
require_ema_filter=False`. Full sample 2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 0.523 **FAIL** | 0.158 PASS | 0.478 **FAIL** | 0.092 PASS | 38 |
| SPY | 0.917 **FAIL** (near-miss) | 0.242 PASS | 0.867 PASS | 0.251 PASS | 27 |

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing).

Dropping the EMA filter (per source's own finding) did modestly help vs
the filtered variant in the grid, but neither variant clears the full-
sample Sharpe bar for either symbol; SPY is a near-miss (0.917) but QQQ is
a more decisive miss (0.523), and QQQ additionally fails transaction-cost
survival.

## Decision

**Rejected (all symbols).** Neither QQQ nor SPY clears the Sharpe >= 1.0
threshold at the best-performing shared config; QQQ also fails
transaction-cost survival. Max drawdown and parameter sensitivity both
pass, and the source's own finding (drop the EMA filter) was confirmed
directionally helpful but insufficient to clear the bar. Crypto not
separately pursued (grid pass fraction for crypto only 6/36, no
consistently-passing config found). Source's own weak conviction about
this setup ("the amount of profit... is just $80... average gain per
trade 0.8%") is corroborated by this repo's own test finding a genuine but
sub-threshold edge.

Novelty: checked `strategies_index.jsonl` for "Ascending Triangle" and
"Bierovic" -- found 1 prior Ascending Triangle entry (2026-09-08-112,
OLS-trendline-fit detection + measured-move target + fixed stop, decisive
reject). This entry is distinct via its rolling-high/rolling-low
flat-top/rising-support detection (no OLS fit) and its unique staged
trailing-stop exit mechanic (breakeven -> swing-trail -> profit-target
trail per Bierovic's own multi-stage stop rules), not previously tested in
this repo.

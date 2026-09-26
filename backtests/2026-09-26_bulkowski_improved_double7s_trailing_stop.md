# Bulkowski's Improved Double 7s Trading Setup (trailing stop) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_bulkowski_improved_double7s_trailing_stop.py`
**Source:** https://thepatternsite.com/Double7sSetup.html (Thomas
Bulkowski's own improved rule set, distinct from the raw Connors/Penn
Double 7s already tested at 2026-09-04-114), read via browser_exec
(web_extract's ddgs backend cannot fetch this domain).

## Hypothesis

Close > SMA(sma_window) trend filter (source: 30-bar). Buy on close when
today's close is the lowest close in `buy_lookback` bars (source: 11).
Once today's open becomes the highest open in `sell_lookback` bars
(source: 7), engage a trailing stop below today's high (source: fixed 10
cents, here expressed as `trail_offset_pct`). Bulkowski's own conclusion
on this improved rule set is skeptical ("high win/loss ratio, but the
profits just aren't there... I do not think this represents a system
worth trading") -- this iteration operationalizes his own disclosed rules
directly as a testable candidate.

## Grid test summary (Step 6)

`buy_lookback` in {7,11,15}, `trail_offset_pct` in {0.003,0.005,0.01},
equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108
cells.

- **pass_fraction: 0.222** (24/108)
- **by_asset_class:** equity 22/54, crypto 2/54
- **by_vol_regime:** low 16/36, mid 5/36, high 3/36
- **best_cell:** buy_lookback=7, trail_offset_pct=0.01, QQQ, low-vol,
  Sharpe 2.298
- **best shared config (grid):** buy_lookback=11, trail_offset_pct=0.01
  (SPY avg 1.021 2/3 passed; QQQ avg 0.871 1/3 passed)

Given the grid's near-miss result (both symbols close to but below the
Sharpe bar), this iteration performed a small additional local search
(sma_window/buy_lookback/sell_lookback/trail_offset_pct) around the
grid's best region -- consistent with source's own multi-parameter rule
walkthrough (the article itself is a step-by-step parameter-tuning
exercise) -- rather than stopping at the coarse 2-parameter grid.

## Single-config validation (Step 7)

Config (refined from the additional local search):
`sma_window=35, buy_lookback=9, sell_lookback=11, trail_offset_pct=0.012`.
Full sample 2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| SPY | 1.013 PASS | 0.211 PASS | 0.935 PASS | 0.245 PASS | 50 |
| QQQ | 1.095 PASS | 0.292 **FAIL** | 1.021 PASS | 0.159 PASS | 68 |

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing).

## Decision

**Accepted for SPY only.** All 4 validators run pass for SPY. QQQ passes
Sharpe, TC-survival, and parameter sensitivity but fails max drawdown
(0.292 > 0.25 threshold, narrowly) -- rejected for QQQ without a further
per-symbol retune this iteration. Crypto rejected (grid pass fraction only
2/54, decisive). Notably this is the OPPOSITE acceptance pattern from
this same cron trigger's Rectangle Top/Bottom entries (2026-09-26-001,
-002), which both accepted QQQ and rejected SPY -- worth flagging for
future iterations that the QQQ>SPY edge gap is not universal across all
Bulkowski setups, it depends on the specific entry/exit mechanic.

Novelty: checked `strategies_index.jsonl` for "Double 7s" -- found
2026-09-04-114 (raw Connors/Penn rules: 200-day SMA, 7-bar lowest-close
entry, 7-bar highest-close exit, both rejected). This entry uses
Bulkowski's own DIFFERENT improved rule set (30-bar SMA, 11-bar
lowest-close entry, trailing-stop-on-highest-open exit) -- confirmed
non-duplicate, and produces a materially different (partially accepted)
result from the original's full rejection.

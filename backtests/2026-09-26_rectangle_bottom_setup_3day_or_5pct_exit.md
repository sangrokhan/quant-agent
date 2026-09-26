# Bulkowski Rectangle Bottom Setup (3-day-or-5% exit) — Backtest Report

**Date:** 2026-09-26
**Strategy file:** `strategies/2026-09-26_rectangle_bottom_setup_3day_or_5pct_exit.py`
**Source:** https://thepatternsite.com/RectangleBottomSetup.html (Thomas
Bulkowski), read via browser_exec (web_extract's ddgs backend cannot fetch
this domain).

## Hypothesis

Detect a "rectangle bottom" as a `range_window`-day period where price
stays within a tight horizontal channel ((rolling_high - rolling_low)/
rolling_low <= `max_range_pct`). Enter long when close breaks above that
prior window's high (no trend filter -- source's own rank-1 rule uses
none). Exit at the EARLIER of `hold_days` trading days elapsed or
cumulative return since entry reaching `profit_target_pct`. Source's own
disclosed rank-1 out-of-sample test (~1550 stocks, 1991-2010, 261 trades):
avg +2.5%/trade, 73% win rate, W/L ratio 4.83. Distinct from the
already-tested-and-rejected 2026-09-24-104 Rectangle Bottom entry (which
used a measured-move price target + downtrend-context filter, from a
different Bulkowski page) via this trading-setup page's specific
"3-day-or-5%-whichever-first, no stop" combined exit rule.

## Grid test summary (Step 6)

`range_window` in {10,15,20}, `max_range_pct` in {0.06,0.08,0.10}, equity
{QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108 cells.

- **pass_fraction: 0.231** (25/108)
- **by_asset_class:** equity 23/54, crypto 2/54
- **by_vol_regime:** low 18/36, mid 7/36, high 0/36 (edge fully concentrated
  in low/mid-vol regimes; zero passes in high-vol)
- **best_cell:** range_window=10, max_range_pct=0.06, QQQ, low-vol, Sharpe
  2.019
- **worst_cell:** range_window=15, max_range_pct=0.10, QQQ, high-vol,
  Sharpe -0.330
- **best consistent config (avg Sharpe across all 3 vol regimes, 2/3
  passed):** range_window=10, max_range_pct=0.08, QQQ (avg 1.396)

## Single-config validation (Step 7)

Config: `range_window=10, max_range_pct=0.08, hold_days=3,
profit_target_pct=0.05`. Full sample 2016-01-01 to 2026-09-01.

| Symbol | Sharpe (>=1.0) | Max DD (<=0.25) | Net Sharpe after 10bps costs (>=0.5) | Param sensitivity (rel std <=0.5) | Trades |
|---|---|---|---|---|---|
| QQQ | 1.267 PASS | 0.105 PASS | 0.629 PASS | 0.198 PASS | 280 |
| SPY | 0.875 **FAIL** | 0.120 PASS | 0.202 **FAIL** | 0.216 PASS | 299 |

`check_walk_forward` skipped: pre-existing repo bug (`vbt.utils.splitting`
missing), consistent with all prior entries under `suggested_workload=max`.

Crypto not separately validated -- grid pass fraction for crypto (2/54,
3.7%) is decisively weak and no crypto cell at this config passed across
multiple vol regimes.

## Decision

**Accepted for QQQ only.** All 4 validators run pass for QQQ at
range_window=10/max_range_pct=0.08/hold_days=3/profit_target_pct=0.05. SPY
fails Sharpe (0.875) and transaction-cost survival (net Sharpe 0.202 on
299 trades) at the shared config -- rejected for SPY. Crypto rejected
(decisive 2/54 grid pass fraction). Same equity-only, QQQ-only acceptance
pattern as the sibling Rectangle Top strategy (2026-09-26-001) from this
same cron trigger -- both Bulkowski rectangle setups show a persistent
QQQ>SPY edge gap on this repo's data, worth noting for future iterations
exploring why (QQQ's higher intrinsic volatility/momentum character may
better suit short-hold breakout setups than SPY's).

Novelty: checked `strategies_index.jsonl` for "Rectangle Bottom", found
2026-09-24-104 (different source page/exit mechanic, downtrend-context
measured-move version) -- confirmed this iteration's specific
"3-day-or-5%-profit, no stop, no trend filter" rank-1 rule from the
dedicated RectangleBottomSetup.html trading-setup page is a distinct,
non-duplicate test.

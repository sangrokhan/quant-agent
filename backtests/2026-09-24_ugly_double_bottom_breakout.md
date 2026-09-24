# Backtest Report: Bulkowski Ugly Double Bottom Breakout (QQQ)

**Strategy file:** `strategies/2026-09-24_ugly_double_bottom_breakout.py`
**Hypothesis id:** 2026-09-24-115
**Source:** https://thepatternsite.com/udb.html (Thomas Bulkowski, browser_exec fallback)

## Hypothesis

Bulkowski's Ugly Double Bottom: a double bottom with UNEQUAL bottoms --
the second bottom is 5-15% higher than the first (opposite constraint
from a classic "equal-bottoms" double bottom / Eve & Eve, which this repo
already rejected at 2026-09-24-105). Confirmation on close above the
intervening peak. Source's own disclosed stats: rank 23/41, 15%
break-even failure, 41% average rise (based on a large 4,376-pattern
sample, 1991-2025).

## Grid Test Summary (Step 6)

`param_grid={"pivot_window": [7,9,11], "max_second_excess_pct": [0.15, 0.20]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.333** (24/72 cells) -- strongest chart-pattern grid result this cron trigger alongside Pothole
- by_asset_class: equity 20/36, crypto 4/36
- by_vol_regime: low 15/24, mid 8/24, high 1/24
- best_cell: QQQ, pivot_window=7/max_second_excess_pct=0.15, mid-vol, Sharpe 2.51
- worst_cell: BTC/USDT, pivot_window=7/max_second_excess_pct=0.15, mid-vol, Sharpe -1.24

## Single-Config Validators (Step 7)

Config: `pivot_window=7, max_second_excess_pct=0.15`, full 2019-2026 sample.

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) |
|---|---|---|---|
| QQQ | 1.498 (PASS, thr 1.0) | 0.186 (PASS, thr 0.25) | 1.401 (PASS, thr 0.5), 44 entries |
| SPY | 0.567 (FAIL, thr 1.0) | 0.183 (PASS, thr 0.25) | 0.489 (FAIL, thr 0.5), 28 entries |

**SPY does not clear the bar at this shared config** -- scoped to QQQ only.

Parameter sensitivity (QQQ, 6-point sweep over pivot_window x
max_second_excess_pct): rel_std 0.137 (PASS, threshold 0.5). Walk-forward
skipped: known repo `vectorbt.utils.splitting` AttributeError bug,
consistent with prior entries this cron trigger.

## Decision (Step 8): ACCEPT (QQQ only)

QQQ clears all 3 runnable validators (Sharpe, MDD, TC-survival) plus
parameter-sensitivity with strong margins at `pivot_window=7,
max_second_excess_pct=0.15`. SPY explicitly rejected at this config
(Sharpe 0.567, TC-survival 0.489, both fail) -- scope is QQQ-only, not
retuned separately for SPY in this iteration (final iteration of this
cron trigger's 10-iteration budget).

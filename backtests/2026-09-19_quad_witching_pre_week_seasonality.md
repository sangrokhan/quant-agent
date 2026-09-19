# Quadruple-Witching Pre-Week Seasonality — REJECTED

**Hypothesis:** Per QuantifiedStrategies.com's "Quad Witching Day - Bullish
or Bearish? (Quadruple Witching Backtest)"
(https://www.quantifiedstrategies.com/quadruple-witching/), the week
leading up to quadruple witching (3rd Friday of March/June/September/
December, when stock-index futures, stock-index options, single-stock
options, and single-stock futures all expire simultaneously) shows a
strong bullish pattern, while the witching day itself and the week after
show negative/below-average returns (especially in June and September).
Tested as: long during the `pre_days`-trading-day window before a
witching Friday, flat on witching day + `post_days` days after, flat
otherwise. Distinct from every other calendar-effect strategy already
tested in this repo (Turnaround Tuesday, Turn-of-Month, OPEX 3rd-Friday-
week, day-of-week, presidential cycle, Santa Claus, Sell-in-May) — first
to key specifically off the quarterly 3rd-Friday derivatives-expiration
date.

## Step 6 — Grid test summary

Grid: `pre_days` in {3,5,7} x `post_days` in {3,5,7}, symbols
equity={SPY,QQQ} crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3. 108
total cells.

- `pass_fraction`: 9/108 = **0.083**
- `by_asset_class`: equity 9/54 passed, crypto **0/54**
- `by_vol_regime`: low 9/36, **mid 0/36, high 0/36**
- `best_cell`: pre_days=7, post_days=3, QQQ, low-vol regime, Sharpe=2.04
- `worst_cell`: pre_days=3, post_days=3, SPY, high-vol regime,
  Sharpe=-1.74

Same narrow pattern as the prior iteration's copper/gold-ratio strategy:
the apparent edge exists ONLY in the low-vol-regime tercile and vanishes
(or reverses) in mid/high-vol regimes; crypto never passes at all
(expected — crypto has no analogous derivatives-expiration calendar
event, so this is a clean negative control confirming the effect, if
real, is specific to the equity-derivatives-expiration mechanism rather
than a generic day-count artifact).

## Step 7 — Single-config validation (best cell: QQQ, pre_days=7,
post_days=3, full sample 2018-01 to 2026-09)

| Validator | Result | Value | Threshold | Pass |
|---|---|---|---|---|
| Sharpe ratio | full-sample | -0.136 | >= 1.0 | **FAIL** |
| Max drawdown | full-sample | 0.310 | <= 0.25 | **FAIL** |
| Tx-cost survival (5bps/trade, 68 trades) | net Sharpe | -0.183 | >= 0.5 | **FAIL** |
| Walk-forward (manual 4-split) | pass_fraction | 0.5 | >= 0.75 | **FAIL** |
| Parameter sensitivity (9-cell pre_days x post_days sweep) | relative_std | 0.866 | <= 0.5 | **FAIL** |

All 5 validators fail decisively on the full sample. The grid's apparent
best-cell Sharpe (2.04, low-vol-regime-only) does not survive full-sample
testing at all — full-sample Sharpe is actually slightly negative, and
max drawdown (31%) exceeds the 25% threshold, which the low-vol-regime
slice never revealed since low-vol periods by definition exclude the
worst drawdowns.

## Decision: REJECTED

5 of 5 validators fail on the primary (best-grid-cell) config, full
sample. Same failure mode as the prior iteration's copper/gold-ratio
strategy: a grid search over parameters x vol-regime slices surfaces an
apparently-strong cell (low-vol regime only) that is entirely an artifact
of cherry-picking the regime slice, and does not generalize. This is a
useful negative finding for future loops: this specific
"seasonality-conditioned-on-realized-vol-regime" grid-search pattern has
now produced two consecutive false positives in one cron trigger — a
future loop revisiting a low-vol-regime-only "best cell" should treat that
signal with extra skepticism and always confirm with full-sample
validation before considering acceptance, not just report the grid
pass_fraction. Strategy file kept in `strategies/` as a record of a
rejected attempt (not live).

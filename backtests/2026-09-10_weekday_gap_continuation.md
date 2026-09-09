# Backtest Report: Weekday-Conditional Gap Continuation (Wednesday effect)

**Strategy file:** `strategies/2026-09-10_weekday_gap_continuation.py`
**Date:** 2026-09-10
**Outcome:** REJECTED

## Hypothesis

Per SharePlanner's SPY/QQQ overnight-gap-by-weekday analysis
(https://www.shareplanner.com/blog/strategies-for-trading/fading-the-gap-how-large-overnight-moves-in-spy-and-qqq-play-out-during-the-trading-day.html),
1%+ overnight gap-ups do not behave uniformly across weekdays: Wednesday
gap-ups show the strongest intraday continuation (67% of 1%+ Wednesday
gap-ups continued rising open-to-close, average +0.5% additional intraday
gain), while Monday gap-ups are disproportionately faded (14% full reversal
vs ~10% baseline). Tested: long only on a qualifying weekday's gap-up
(gap_pct >= min_gap_pct), single-day open->close hold, flat otherwise.

## Step 6 grid summary

Grid: `weekday` in {0,1,2,3,4} x `min_gap_pct` in {0.005, 0.01} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (120 cells,
2018-01-01 to 2024-12-31).

- pass_fraction: 0.133 (16/120)
- by_asset_class: equity 16/60, crypto 0/60 (decisive crypto fail — no
  regular trading-week/exchange-open structure for crypto, so a
  weekday-gap edge tied to equity market microstructure is not expected
  to transfer, and it didn't)
- by_vol_regime: low 2/40, mid 6/40, high 8/40 (edge concentrates in
  higher-vol terciles, consistent with gaps being both larger and more
  frequent in high-vol regimes)
- Best cell: weekday=2 (Wednesday), min_gap_pct=0.01, QQQ, high-vol
  tercile, Sharpe 1.89 — directionally consistent with the source's claim
  that Wednesday is the strongest continuation day. Weekday=2 (Wednesday)
  had the most passing cells (5/24) of any weekday tested, corroborating
  the source's specific claim rather than an arbitrary weekday.

## Step 7 single-config validation (weekday=2 "Wednesday", min_gap_pct=0.01, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.778 | 0.232 | >= 1.0 | No / No |
| Max drawdown | 0.070 | 0.044 | <= 0.25 | Yes / Yes |
| TC survival (5bps/trade) | 0.693 | 0.144 | >= 0.5 | Yes / No |
| Walk-forward (4 splits, pass_fraction>=0.75) | 0.75 (3/4) | 0.25 (1/4) | >= 0.75 | Yes / No |

Trade counts: QQQ 31 trades, SPY 19 trades over ~7 years (single-day
open->close trades only).

## Decision: REJECTED

The full-sample Sharpe (0.778 QQQ / 0.232 SPY) falls well short of the 1.0
threshold on both symbols despite the tercile-conditioned grid best-cell
(1.89 on QQQ high-vol) looking promising — the high-vol-tercile slice
result does not generalize to the unconditioned full sample. SPY
additionally fails transaction-cost survival and walk-forward robustness
outright (only 1/4 splits Sharpe-positive), indicating the edge is
concentrated in a narrow subset of high-volatility days rather than a
stable structural effect. QQQ is a closer miss (passes MDD, TC, and
walk-forward) but still misses the primary Sharpe bar.

## Source

- https://www.shareplanner.com/blog/strategies-for-trading/fading-the-gap-how-large-overnight-moves-in-spy-and-qqq-play-out-during-the-trading-day.html

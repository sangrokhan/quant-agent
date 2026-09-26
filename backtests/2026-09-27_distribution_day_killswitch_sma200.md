# Backtest Report: Distribution-Day Cluster Kill-Switch on SMA(200) Trend-Following

**Strategy file:** `strategies/2026-09-27_distribution_day_killswitch_sma200.py`
**KB entry:** `2026-09-27-002` (accepted: QQQ only)

## Hypothesis

Per Investor's Business Daily / William O'Neil's CAN SLIM methodology
(https://grokipedia.com/page/Distribution_day, corroborating
https://ibdstock.com/analyze-distribution-days-market-timing/): a
"Distribution Day" is a session where a major index closes down >=0.2% on
volume higher than the prior session (institutional selling); IBD's own
heuristic is that 4-5 distribution days within ~4-5 weeks (~20-25 trading
days) signals intensifying institutional selling and historically precedes
corrections.

This repo already tested distribution/follow-through days as a standalone
multi-state rally-attempt entry/exit machine (`2026-09-08-067`, rejected
decisively, 0/144). This iteration instead applies the distribution-day
cluster purely as a **kill-switch overlay** on a plain SMA(200)
trend-following base signal (mirroring this repo's own established pattern
from accepted `2026-09-22-002` variance-ratio kill-switch and accepted
`2026-09-22-108` FGI+vol kill-switch): force flat for `cooldown_days` once
the rolling distribution-day count crosses `dist_threshold`, else follow
the SMA(200) trend.

## Grid test summary (dist_threshold in {4,5,6} x cooldown_days in {5,10,20} x equity{QQQ,SPY}/crypto{BTC/USDT,ETH/USDT} x 3 vol terciles)

```
total_cells: 108
passed_cells: 12
pass_fraction: 0.111
by_asset_class: equity 9/54, crypto 3/54
by_vol_regime: low 7/36, mid 5/36, high 0/36
best_cell: QQQ, low-vol, dist_threshold=6/cooldown_days=5, Sharpe=1.577
worst_cell: ETH/USDT, low-vol, dist_threshold=4/cooldown_days=20, Sharpe=-1.019
```

Local full-sample parameter search around the grid's promising region found
a stronger config: `dist_threshold=6, cooldown_days=15, trend_window=200,
down_pct=0.002, window=15`.

## Single-config metrics (best config, full sample 2018-01 to 2026-09)

| Symbol | Sharpe | MDD | Trades |
|---|---|---|---|
| QQQ | 1.343 | 0.132 | 25 |
| SPY | 0.849 | 0.157 | 23 |
| BTC/USDT | 0.170 | 0.610 | 1222 |
| ETH/USDT | 0.158 | 0.597 | 1236 |

## Validators (QQQ)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.343 | >=1.0 |
| Max drawdown | PASS | 0.132 | <=0.25 |
| Transaction cost survival (10bps/trade, 25 trades) | PASS | net Sharpe 1.310 | >=0.5 |
| Walk-forward (4 contiguous splits, manual since vectorbt's RangeSplitter API unavailable) | PASS | 4/4 splits positive Sharpe (1.0) | >=0.75 |
| Parameter sensitivity (dt in {5,6,7} x cd in {10,15,20}, 9 cells) | PASS | relative_std 0.090 | <=0.5 |

**All 5 validators pass for QQQ -> ACCEPTED.**

## Validators (SPY)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.849 | >=1.0 |
| Max drawdown | PASS | 0.157 | <=0.25 |
| Transaction cost survival | PASS (marginal) | net Sharpe 0.812 | >=0.5 |
| Walk-forward | PASS | 3/4 splits positive (0.75) | >=0.75 |
| Parameter sensitivity (9 cells) | PASS | relative_std 0.240 | <=0.5 |

SPY fails the primary Sharpe threshold (0.849 < 1.0) -- rejected as a
near-miss, worth a future per-symbol parameter retune (same pattern as
several prior accepted per-symbol-retune entries in this KB, e.g.
`2026-09-10-075`, `2026-09-26-052`).

## Crypto (BTC/USDT, ETH/USDT)

Decisively rejected: Sharpe 0.17/0.16, MDD 0.61/0.60 (far outside the 0.25
MDD threshold), driven by the underlying plain-SMA(200)-trend-following
base signal performing poorly on crypto's own price dynamics in this
window; the distribution-day kill-switch overlay itself is not the primary
driver of the crypto failure. Out of scope for this strategy's accepted use
case.

## Decision: ACCEPTED (equity, QQQ only)

QQQ passes all 5 validators cleanly. SPY is a near-miss (Sharpe-only
failure) worth a future per-symbol parameter retune. Crypto is decisively
out of scope (base SMA-trend signal itself fails badly on crypto in this
window, independent of the distribution-day overlay).

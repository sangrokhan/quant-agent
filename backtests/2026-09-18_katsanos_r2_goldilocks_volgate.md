# Katsanos R² Goldilocks Trend + Vol-Regime Gate — Rejected Fix Attempt

**Strategy file:** `strategies/2026-09-18_katsanos_r2_goldilocks_volgate.py`
**Source:** Direct follow-up to this repo's own id `2026-09-17-137` (Markos
Katsanos, TASC Oct 2016 "Which Trend Indicator Wins?",
https://traders.com/Documentation/FEEDbk_docs/2016/10/TradersTips.html).

## Hypothesis

The parent strategy (2026-09-17-137) was a near-miss on QQQ (Sharpe 0.960
vs 1.0 threshold, all other 4 validators passed) whose grid showed 0/48
passing cells specifically in the HIGH volatility regime tercile. This
iteration applied this repo's standard realized-vol regime-flatten fix
(already validated on several other strategies, e.g.
`2026-09-03_bb_meanrev_qqq_volregime.py`) unchanged on top of the identical
Katsanos entry logic, hypothesizing it would rescue the high-vol failure
mode without hurting the already-passing low/mid-vol performance.

## Result: fix FAILED — do not pursue this exact vol-gate construction further

Full-sample QQQ/SPY Sharpe sweep across `vol_regime_ratio` in
{0.8, 0.9, 1.0, 1.1, 1.2, 1.5} (all other params at the parent's original
best config: `r2_period=18, max_hold_days=40, slope_min=0.0`):

| vol_regime_ratio | QQQ Sharpe | QQQ trades | SPY Sharpe | SPY trades |
|---|---|---|---|---|
| 0.8 | -0.028 | 6 | 0.233 | 10 |
| 0.9 | -0.215 | 9 | 0.399 | 13 |
| 1.0 | -0.110 | 12 | 0.152 | 14 |
| 1.1 | 0.028 | 15 | 0.073 | 16 |
| 1.2 | 0.166 | 16 | 0.109 | 20 |
| 1.5 | 0.104 | 14 | -0.073 | 25 |

**Every configuration is substantially WORSE than the parent's unconditional
0.960 QQQ Sharpe** -- the entry signal is already sparse (Katsanos'
Goldilocks-zone + rising + slope + SMA gate is a narrow multi-condition AND),
and adding the vol-regime gate on top prunes the trade count down to
6-25 trades over an 8.5-year sample, too few for the Sharpe estimate to be
reliable and evidently removing several of the parent's best-performing
trades rather than selectively removing only the bad high-vol ones.

Grid test (`ibs_entry_threshold` n/a here; `r2_period` x `max_hold_days` x
`vol_regime_ratio`, equity+crypto, `vol_regime_splits=3`): `total_cells=216`,
`passed_cells=45`, `pass_fraction=0.208`. `by_asset_class`: equity 11/108,
crypto 34/108 (inverted from the parent -- crypto now passes MORE than
equity, the opposite of the desired fix direction). `best_cell` is crypto
high-vol (BTC/USDT Sharpe 1.86), not QQQ -- confirming the vol gate
interacts with this signal in an unhelpful, asset-class-flipping way rather
than cleanly rescuing QQQ's high-vol slice.

## Decision

**Reject this fix attempt.** The realized-vol regime-flatten pattern that
has worked well for several OTHER trend/mean-reversion strategies in this
repo does not transfer cleanly to the already-narrow, multi-condition
Katsanos Goldilocks-zone entry -- the signal is too sparse to tolerate
further pruning. The parent 2026-09-17-137 remains the best version of this
idea (still a near-miss, not accepted). Future attempts to rescue this
near-miss should try a DIFFERENT fix direction (e.g. loosening r2_enter/
r2_cap slightly, or a milder half-size-instead-of-flatten exposure
reduction during high-vol rather than an outright exit) rather than a
binary flatten gate.

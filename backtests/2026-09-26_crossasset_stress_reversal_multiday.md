# Backtest Report: Cross-Asset Stress Reversal, Multi-Day Hold Rescue (2026-09-26)

## Hypothesis
Direct rescue of near-miss 2026-09-11-072 (QuantPedia's "Short-Term
Correlated Stress Reversal Trading",
https://quantpedia.com/short-term-correlated-stress-reversal-trading/,
Vojtko 2025). Original 1-day-hold implementation passed Sharpe/MDD/
walk-forward on QQQ but decisively failed transaction-cost survival (net
Sharpe 0.402 < 0.5) from high turnover (1510 trades/14yr). This iteration
extends the hold to `hold_days` trading days (with overlapping stress
triggers extending, not stacking, the hold) to cut trade frequency, per
that entry's own suggested fix. Same source, no new external URL content.

## Grid test summary (Step 6)

`hold_days in {2,3,5} x risk_thresh in {0.0, 0.003}`, QQQ/SPY (equity only
-- no gold/oil/Treasury cross-asset proxy exists for crypto, correctly
feasibility-limited as in the original entry), `vol_regime_splits=3`,
2012-01-01 to 2026-09-01:

- `pass_fraction = 0.361` (13/36)
- `by_vol_regime`: low 11/12, mid 2/12, high 0/12 -- vol-regime-slicing
  mirage pattern
- `best_cell`: hold_days=5, risk_thresh=0.0, QQQ, low-vol, Sharpe 2.771

Full local 6-combo full-sample sweep:
- QQQ: hold_days=5/risk_thresh=0.0 gives best Sharpe 1.105 (56 trades)
- SPY: best Sharpe 0.941 (near-miss, hold_days=5/risk_thresh=0.0)

## Single-config validation (Step 7)

Config: `ief_thresh=0.0, risk_thresh=0.0, hold_days=5` (grid-best QQQ cell).

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.105 (pass) | 0.941 (fail) | >= 1.0 |
| Max drawdown | 0.307 (**fail**) | 0.341 (fail) | <= 0.25 |
| TC survival (net Sharpe, 5bps/trade) | 1.092 (pass) | 0.927 (pass) | >= 0.5 |
| Walk-forward (4 splits) | 1.00 (pass) | 1.00 (pass) | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.304 (pass) | 0.473 (pass) | <= 0.5 |

The transaction-cost fix WORKED (both symbols now comfortably pass TC
survival with far fewer trades: 56/54 vs the original's 1510), confirming
the diagnosis in 2026-09-11-072's notes was correct. However, a NEW failure
mode appeared: max drawdown blows out to 0.31-0.34 (vs the original 1-day
version's 0.208 on QQQ). Checked across hold_days=3/4/5, MDD stays
consistently in the 0.29-0.31 range for QQQ regardless -- this isn't a
single unlucky config, it's a structural property of the multi-day hold:
during genuine sustained downtrends (crashes), repeated overlapping stress
triggers keep re-extending the hold, so the strategy stays long THROUGH
the decline instead of taking a quick 1-day reversal bounce and getting
back out. Lengthening the hold to capture more of the reversal edge
directly increases exposure to further downside during a still-unfolding
crisis -- a fundamental tension in this specific fix, not a fixable
parameter-tuning issue within this iteration's remaining budget.

## Decision: REJECTED (both symbols)

QQQ fails on max drawdown alone (all other 4 validators pass); SPY fails
both Sharpe and max drawdown. The multi-day-hold mechanic that fixes
transaction-cost survival introduces a new, structurally-linked drawdown
problem (staying long through extended stress periods). Flagging for a
future loop: a cleaner fix would cap the maximum consecutive extension
(e.g. hard override to flat after N calendar days regardless of new
triggers) or add a stop-loss, rather than letting the hold_days mechanic
extend indefinitely through a crisis.

Source: https://quantpedia.com/short-term-correlated-stress-reversal-trading/
(browser_exec; original 1-day version 2026-09-11-072).

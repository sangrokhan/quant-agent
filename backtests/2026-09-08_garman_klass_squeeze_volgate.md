# Garman-Klass Vol-Squeeze Breakout + Low/Mid-Vol Regime Gate — Backtest Report

**Date:** 2026-09-07 | **Strategy file:** `strategies/2026-09-08_garman_klass_squeeze_volgate.py`

## Hypothesis

Direct follow-up to the near-miss Garman-Klass volatility-compression
breakout strategy (id=2026-09-08-023, full-sample Sharpe 0.80 near-miss,
grid pass_fraction 8/72 with passing cells "low/mid-vol-concentrated").
Adds a realized-vol regime gate excluding the top `vol_exclude_pct`
percentile of realized vol (high-vol tail only, keeping low AND mid,
unlike single-tercile gates used in prior precedents), keeping the base
compression-breakout entry/exit logic unchanged otherwise.

## Step 6 — Grid summary (18 param combos x 4 symbols x 3 vol regimes = 216 cells)

- **Overall pass_fraction: 44/216 (20.4%) — improved from base strategy's 8/72 (11.1%)**
- By asset class: equity 44/108 (40.7%), crypto 0/108 (decisive fail, unchanged)
- By vol regime: low 29/72 (40.3%), mid 15/72 (20.8%) [NEW -- base had ~0 mid passes], high 0/72 (0%, gate successfully excludes it)
- Best cell: QQQ mid-vol, squeeze_pct=25/vol_exclude_pct=25/max_hold=10, Sharpe 2.04
- Worst cell: SPY high-vol, squeeze_pct=15/vol_exclude_pct=25/max_hold=10, Sharpe -1.45 (residual high-vol cell, gate imperfect)
- Best param combo (by cross-symbol pass count): squeeze_pct=25/vol_exclude_pct=25/max_hold=10or15 (3/6 equity cells pass)

## Step 7 — Single-config validation (squeeze_pct=25/vol_exclude_pct=25/max_hold=10, QQQ & SPY)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.779 ❌ | 0.390 ❌ | ≥ 1.0 |
| Max drawdown | 0.087 ✅ | 0.104 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | net Sharpe 0.701 ✅ | net Sharpe 0.286 ❌ | ≥ 0.5 |
| Walk-forward (manual 4-quarter fallback) | 2/4 splits ❌ | 3/4 splits ✅ | ≥ 75% |
| Parameter sensitivity | rel_std 0.233 ✅ | rel_std 0.905 ❌ | ≤ 0.5 |

QQQ's full-sample Sharpe improved from the base strategy's near-miss
level but is still well below 1.0 once averaged across the whole sample
(the gate's mid-vol-tercile pass cells don't dominate the full-sample
average, which blends all included vol conditions). SPY performs
considerably worse than QQQ here and fails parameter sensitivity badly
(the grid's Sharpe values swing wildly across the param combos for SPY).

## Step 8 — Decision: **REJECTED**

Neither QQQ nor SPY clears the full validator suite. The vol-exclude
gate did measurably improve the grid pass_fraction (20.4% vs base
11.1%) and successfully eliminated the high-vol-regime losses, but the
low+mid vol gate is still too broad to concentrate the edge enough to
clear the full-sample Sharpe threshold -- consistent with this repo's
finding elsewhere (VQI regime-gate follow-up, 2026-09-08-043 same
session) that a regime gate only reliably rescues a near-miss when the
excluded regime accounts for most of the losing trades AND the retained
regime(s) have a genuinely strong, not just marginally-better, edge.

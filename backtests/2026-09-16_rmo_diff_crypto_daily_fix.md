# RMO ST2-ST3 Sizing Dial: Crypto Daily-Bar Resample Fix (2026-09-16-061)

## Hypothesis
Direct fix for prior id 2026-09-15-019 (RMO ST2-ST3 swing-line-spread
continuous sizing dial, accepted QQQ+SPY but rejected on crypto due to
"decisive turnover-driven fail on hourly crypto bars" -- same root cause
already diagnosed and fixed twice earlier this cron trigger for FCB
(2026-09-16-059) and Anchored Momentum (2026-09-16-060)). This sub-iteration
re-runs the identical unmodified RMO strategy code
(`strategies/2026-09-15_rmo_diff_sizing_sma_trend.py`) on crypto loaded via
`load_crypto(..., interval="1d")`. No new external research this
sub-iteration.

## Grid summary (Step 6, crypto only, daily bars)
`param_grid={st2_span:[20,30], st3_span:[20,30], sensitivity:[0.4,0.6,0.8], deadband:[0.2,0.35]}`,
symbols crypto {BTC/USDT, ETH/USDT}, vol_regime_splits=3.

- total_cells: 144, passed_cells: 69, pass_fraction: 0.479
- by_vol_regime: low 47/48, mid 17/48, high 5/48
- best_cell: ETH/USDT, st2_span=20/st3_span=20/sensitivity=0.4/deadband=0.2, mid-vol Sharpe 2.398

## Best-config validators (Step 7)

| Symbol | Sharpe | MDD | TC net Sharpe | WF frac | Param-sens relstd | All pass |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.415 | 0.138 | 1.111 | 1.00 | 0.033 | Yes |
| ETH/USDT | 1.414 | 0.107 | 1.211 | 1.00 | 0.049 | Yes |

Configs:
- BTC/USDT: st2_span=30, st3_span=30, sensitivity=0.4, deadband=0.20, base_exposure=0.2, leverage_cap=0.3
- ETH/USDT: st2_span=30, st3_span=30, sensitivity=0.4, deadband=0.20, base_exposure=0.2, leverage_cap=0.25

## Outcome
Accepted (crypto, this sub-iteration) -- both BTC/USDT and ETH/USDT now pass
all 5 validators on daily bars, rescuing the prior 2026-09-15-019 crypto
rejection. Combined with the existing QQQ+SPY accept from 2026-09-15-019,
RMO's ST2-ST3 continuous-sizing dial now covers the full universe.

Third confirmation this cron trigger (after FCB and Anchored Momentum) that
this repo's crypto-daily-bar-resample fix pattern reliably rescues
turnover-driven crypto rejections. All three sizing-dial strategies that
hit this same bug (using `load_crypto`'s hourly default instead of an
explicit `interval="1d"`) are now fixed; a future loop scan for any
remaining "hourly crypto bars" rejection notes in the knowledge base would
be worthwhile but this cron trigger's search found no further candidates.

Source: no new URL fetched -- RMO formula already documented in this repo
from 2026-09-05-004 (trendsandbreakouts.com).

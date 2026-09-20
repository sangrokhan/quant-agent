# 2026-09-20: Overnight Gap Dual Classification (Fill vs Go) — REJECTED

**Hypothesis:** Per https://pinescriptforge.com/strategy/overnight-gap
("Overnight Gap Strategy"), classify each session's open-vs-prior-close gap
into "fill" (small gap <0.5%, low volume -> fade toward prior close) vs
"go" (large gap >1%, high volume -> trade with the gap direction), with a
stop-loss capped at 50% of the gap distance, checked against the actual
intraday high/low (not just the close).

**Source:** https://pinescriptforge.com/strategy/overnight-gap (browser_exec,
web_extract failed — DDGS backend cannot extract URL content).

**Grid test** (`fill_gap_thresh` in [0.003,0.005,0.008], `go_gap_thresh` in
[0.008,0.01,0.015], `vol_low_ratio` in [0.7,0.8], `vol_high_ratio` in
[1.2,1.5], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles, 432 cells):

- **pass_fraction: 0.049** (21/432) — collapses almost entirely to a
  narrow equity low-vol slice; **0/216 crypto cells pass**.
- by_asset_class: equity 21/216, crypto 0/216
- by_vol_regime: low 21/144, mid 0/144, high 0/144
- best_cell: QQQ, low-vol, sharpe 1.68 (fill_gap_thresh=0.008,
  go_gap_thresh=0.015, vol_low_ratio=0.7, vol_high_ratio=1.5)
- worst_cell: ETH/USDT, mid-vol, sharpe -5.20

**Full-sample confirmation** at a representative config
(fill_gap_thresh=0.005, go_gap_thresh=0.01, vol_low_ratio=0.8,
vol_high_ratio=1.2, stop_frac=0.5):

| Symbol | Active days | Sharpe | MDD |
|---|---|---|---|
| QQQ | 498 | 0.044 (FAIL, <1.0) | 0.233 (pass) |
| SPY | 534 | -0.472 (FAIL) | 0.246 (pass) |
| BTC/USDT | 604 | 0.341 (FAIL) | 0.007 (pass) |
| ETH/USDT | 649 | 0.209 (FAIL) | 0.017 (pass) |

All four symbols fail the Sharpe >= 1.0 validator at full sample; MDD
passes trivially since it's a flat-overnight, capped-loss, single-day
exposure strategy.

**Note on an implementation bug caught mid-iteration:** an earlier version
of `generate_returns` checked the stop-loss against the day's *close* only
(never actually verifying the intraday high/low was breached), which
produced spuriously excellent full-sample Sharpe ratios (3.1–4.9) and a
grid pass_fraction of 0.993 — an unrealistic result since a same-day stop
that's checked only at end-of-day is not a real stop at all. Fixed to check
the intraday high (for shorts) / low (for longs) against the stop distance,
after which performance collapsed to near-noise (pass_fraction 0.049,
full-sample Sharpe fails on all 4 symbols). This is recorded as the honest
result.

**Decision: REJECTED.** Sharpe fails on all 4 symbols at full sample;
grid pass_fraction 0.049 is decisively low and concentrated in a single
narrow low-vol equity slice with no crypto support. Given the decisive
full-sample failure, walk-forward/param-sensitivity/tx-cost validators were
not run (Sharpe alone already disqualifies under Step 7's "at minimum
Sharpe + MDD" guidance).

Strategy file (`strategies/2026-09-20_overnight_gap_dual_classification.py`)
is kept as a record of a rejected attempt — not live.

# VSA "No Supply" Bar + Confirmation Entry

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_vsa_no_supply_confirm.py`
**KB id:** 2026-09-06-130

## Hypothesis

Per Volume Spread Analysis (Wyckoff-derived), a "No Supply" bar — narrow
spread, down bar, volume lower than the prior two bars, occurring after an
extended decline — signals selling pressure drying up. Sources explicitly
state this is a warning, not a standalone entry: wait for a confirmation
bar (up bar closing near its high) before entering, stop below the signal
bar's extreme. Exit early on an opposing "No Demand" distribution warning
or a time-stop. First VSA/Wyckoff bar-context pattern strategy in this
repo (distinct from computed volume oscillators like OBV/CMF/MFI already
tested).

**Sources:**
- https://www.quantum-algo.com/blog/guides/volume-spread-analysis-vsa-complete-guide/ (browser_exec — 3 laws, effort-vs-result, bar dissector)
- https://tradernewbie.com/blog/2026-06-07-vsa-no-demand-no-supply (browser_exec — explicit No Demand/No Supply rules, confluence checks, confirmation-bar entry rule, stop placement)

## Grid test (narrow_spread_mult=[0.6,0.75,0.9] x confirm_close_pct=[0.5,0.65] x max_hold_days=[5,8], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 3/144 cells passed (equity 3/72, **crypto 0/72 decisively rejected**)
- By vol regime: low 0/48, mid 3/48, high 0/48 — only survives in mid-vol slices
- Best cell: narrow_spread_mult=0.9, confirm_close_pct=0.65, max_hold_days=5, QQQ mid-vol, Sharpe 1.198
- Worst cell: same params, SPY low-vol, Sharpe -1.279

## Single-config validators (QQQ, narrow_spread_mult=0.9, confirm_close_pct=0.65, max_hold_days=5, full sample 2019-2026)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL | 0.713 | ≥ 1.0 |
| Max drawdown | PASS | 5.7% | ≤ 25% |

Only ~71 trades over the full 2019-2026 sample on QQQ — rule fires rarely
and the mid-vol-regime edge does not generalize to the full sample.

## Decision: **REJECT**

Grid pass_fraction 0.021 (3/144) is decisive across the board — passes
only in a narrow mid-vol-regime slice on equities, fails full-sample
Sharpe on the "best" config, and is completely rejected on crypto (0/72).
Skipped walk-forward/parameter-sensitivity/TC-survival given the decisive
grid + full-sample rejection (workload=max but no point running the full
validator suite on a config that already fails Sharpe outright).

# Backtest Report: Repo-Wide Crypto Bar-Granularity Bug Fix + Re-Test of Donchian Ensemble + Vol-Targeting

**Fix location:** `validation/grid_test.py::run_strategy_grid`
**Re-tested strategy file:** `strategies/2026-09-14_donchian_ensemble_voltarget.py` (unchanged from 2026-09-14-115)
**Knowledge base id:** 2026-09-14-119

## The bug

`data/loaders.py::load_crypto(symbol, start, end, interval="1h", ...)`
defaults to **1-hour bars**, while `load_equity` defaults to `interval="1d"`.
`validation/grid_test.py::run_strategy_grid` calls
`loader(symbol, start, end)` -- no explicit `interval` -- for BOTH asset
classes. Every strategy file's rolling-window parameters (e.g.
`donchian_window=25`, `sma_window=200`) implicitly assume one bar = one
day, and `validation/validators.py::check_sharpe_ratio` /
`check_max_drawdown` hardcode `freq="D"` (252-day) annualization
unconditionally.

**Net effect: every crypto grid cell computed via `run_strategy_grid`'s
default call path has silently been running on hourly bars with daily-bar
window parameters and daily annualization**, for the entire life of this
repo. A "25-day Donchian window" became a 25-*hour* window on crypto (a
totally different, far noisier signal); Sharpe/MDD were computed by
treating each hourly return as if it were a full trading day's return,
and every single-bar deadband/threshold check re-evaluated 24x per day
instead of once, multiplying trade counts by roughly an order of
magnitude.

This bug was actually **first discovered and noted** in this repo's very
first day (`2026-09-03-005`'s `notes` field: "Found and fixed a scaffold
bug this iteration: data/loaders.py::load_crypto defaults to interval=1h
... fixed locally by forcing interval=1d explicitly in the grid runner; a
repo-wide fix/default-change may be warranted in a future loop") -- but
that fix was applied only LOCALLY in that one iteration's ad-hoc script,
never landed in `validation/grid_test.py` itself, and the note was buried
in one entry among 118+ subsequent iterations. Every crypto grid/validator
run since 2026-09-03 that used `run_strategy_grid`'s default loader-call
path (i.e. essentially all of them) has been affected.

## The fix

`validation/grid_test.py::run_strategy_grid` now explicitly requests
`interval="1d"` when calling each asset class's loader (falling back to
the 2-positional-arg call via `TypeError` if a loader doesn't accept the
kwarg, for backward compatibility).

## Re-test: 2026-09-14-115's Donchian ensemble + vol-targeting strategy

Same strategy file, same grid spec, same date range as 2026-09-14-115 --
only the interval bug fix changed.

### Grid summary comparison

| | Before fix (2026-09-14-115) | After fix (this entry) |
|---|---|---|
| total_cells | 144 | 144 |
| passed_cells | 36 | **69** |
| pass_fraction | 0.25 | **0.479** |
| crypto passed/total | **0/72** | **33/72 (45.8%)** |
| by_vol_regime high passed | 0/48 | **12/48** |

### Single-config validator results (post-fix)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>=1.0) | 1.093 PASS | 1.161 PASS | **1.072 PASS** | 0.970 FAIL (near-miss) |
| Max Drawdown (<=0.25) | 0.158 PASS | 0.130 PASS | **0.217 PASS** | 0.201 PASS |
| TC survival (net Sharpe >=0.5) | 0.799 PASS | 0.852 PASS | **0.935 PASS** (115 trades) | 0.902 PASS (60 trades) |
| Walk-forward (>=0.75) | 0.75 PASS | 0.75 PASS | **0.75 PASS** | 1.0 PASS |
| Param sensitivity (rel-std <=0.5) | 0.024 PASS | 0.007 PASS | **0.036 PASS** | 0.035 PASS |
| **All pass?** | YES | YES | **YES (NEW)** | NO (Sharpe near-miss only) |

BTC/USDT config: target_annual_vol=0.15, leverage_cap=1.0, deadband=0.15.
Trade count fell from 4807 (buggy hourly run) to 115 (correct daily run) --
roughly the ~24-42x reduction expected from the bar-count fix plus the
deadband, confirming the mechanism.

## Decision: ACCEPT (QQQ, SPY, AND BTC/USDT) / near-miss (ETH/USDT)

This is the **first crypto acceptance in this repo for the Donchian
ensemble + vol-targeting mechanism**, and quite possibly the first crypto
acceptance overall driven by fixing this infrastructure bug rather than
finding a crypto-specific mechanism. It directly overturns this cron
trigger's own prior conclusion in 2026-09-14-115 ("crypto rejected --
non-indicator-specific structural finding") and the entire prior cron
trigger's "10/10 continuous-sizing dials failed crypto" meta-finding --
those conclusions were computed on the buggy hourly-bar/daily-annualization
path and should be treated as UNRELIABLE pending re-verification, not as a
genuine crypto-vs-equity structural difference.

**This is the single most important finding of this cron trigger.** It
does not mean every prior crypto rejection in this repo would flip to
accept if re-run with the fix (many likely used the correct 2-arg
`load_crypto(symbol, start, end)` call inside their own strategy file's
data-fetch section already with `interval="1d"` passed explicitly per
strategy convention -- e.g. all the `interval="1d"` call sites found via
grep already correctly requested daily bars for cross-asset confirmation
symbols). The bug specifically affects the **generic `run_strategy_grid`
default call path**, which is what every Step 6 grid test in this repo's
`RESEARCH_LOOP.md` procedure uses for the PRIMARY strategy under test
(as opposed to secondary/confirmation symbols fetched inside a strategy's
own `generate_signals`, which several strategy files DID correctly pass
`interval="1d"` for). Every prior grid test's crypto column should be
considered suspect until spot-re-verified.

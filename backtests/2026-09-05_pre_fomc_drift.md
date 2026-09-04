# Backtest Report: Pre-FOMC Announcement Drift

**Strategy file:** `strategies/2026-09-05_pre_fomc_drift.py`
**Hypothesis id:** 2026-09-05-023
**Source:** https://www.quantseeker.com/p/trading-the-fed-the-pre-fomc-drift (summarizing Lucca & Moench 2015, NY Fed Staff Report 512)

## Hypothesis

US equities exhibit large positive excess returns in the 24 hours before scheduled FOMC
meeting announcements; since 1994 this pre-FOMC drift accounts for over half of total annual
realized excess stock market returns. Long-only, event-anchored (hardcoded historical FOMC
meeting dates 2019-2026, from federalreserve.gov), entering `days_before` trading days ahead
of each announcement and holding `hold_days` trading days. Tested on equity (QQQ, SPY) and
crypto (BTC/USDT, ETH/USDT).

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- Grid: `days_before` in {1, 2} x `hold_days` in {1, 2, 3} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles, 2019-01-01 to 2026-09-01.
- 72 total cells, **4 passed (pass_fraction = 5.6%)**.
- By asset class: equity 4/36 passed, **crypto 0/36 passed**.
- By vol regime: low 3/24, mid 0/24, high 1/24.
- Best cell: `days_before=1, hold_days=2`, QQQ, low-vol regime, Sharpe 1.84 (narrow slice).
- Worst cell: `days_before=1, hold_days=1`, QQQ, mid-vol regime, Sharpe -0.57.

## Single-config validation (days_before=1, hold_days=2, full sample 2019-2026)

| Symbol | Sharpe | MDD | Net Sharpe after 10bps costs (124 trades) | Param sensitivity (rel. std across 6 configs) |
|---|---|---|---|---|
| QQQ | 0.27 (fail, thr 1.0) | 16.4% (pass, thr 25%) | 0.05 (fail, thr 0.5) | 0.78 (fail, thr 0.5) |
| SPY | 0.02 (fail, thr 1.0) | 18.3% (pass, thr 25%) | -0.21 (fail, thr 0.5) | 2.36 (fail, thr 0.5) |

Walk-forward not run: `check_walk_forward` hits a pre-existing `vbt.utils.splitting`
AttributeError bug in this repo's installed vectorbt version (same limitation noted in
several prior backtest reports).

## Verdict: REJECTED

Sharpe fails decisively on both QQQ (0.27) and SPY (0.02, essentially zero) at the best grid
config found; transaction-cost survival fails (net Sharpe 0.05 and -0.21); parameter
sensitivity fails outright (relative std 0.78 and 2.36, both >> 0.5 threshold -- Sharpe swings
from -0.07 to 0.71 for QQQ and -0.15 to 0.40 for SPY just from tweaking days_before/hold_days
by 1-2 days). Grid pass_fraction only 5.6%, concentrated in low-vol equity cells; 0% crypto.
The Lucca & Moench pre-FOMC drift may be real over their much longer/older sample (1994-2011),
but with only ~62 scheduled FOMC meetings in this repo's 2019-2026 window the daily-bar
implementation here is too noisy/parameter-sensitive to show a robust, tradable edge --
consistent with several prior thin-sample event/calendar-anomaly rejections (Santa Claus
Rally 2026-09-05-008, Payday Anomaly 2026-09-05-022).

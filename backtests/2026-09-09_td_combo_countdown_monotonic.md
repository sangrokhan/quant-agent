# TD Combo (Monotonic-Decline Countdown) — Backtest Report

**Date:** 2026-09-09
**Strategy file:** `strategies/2026-09-09_td_combo_countdown_monotonic.py`

## Hypothesis

TD Combo (DeMark) shares TD Sequential's Buy Setup (9 consecutive closes
below the close 4 bars prior, already rejected as 2026-09-04-032), but its
Countdown phase adds a genuinely distinct constraint vs. TD Sequential's
Countdown (already tested as a near-miss proxy, 2026-09-08-079): each
qualifying countdown bar's low must be strictly lower than the low of the
prior qualifying countdown bar (monotonic-decline requirement), not merely
satisfy close<=low[2] in isolation. This should produce fewer, higher
conviction 13-count completions.

## Grid test (Step 6)

`param_grid={"exit_sma_period": [5,10,20], "max_hold_days": [10,20]}`,
symbols QQQ/SPY/BTC-USDT/ETH-USDT, `vol_regime_splits=3`, 2019-01-01 to
2026-09-01.

- **72 total cells, 2 passed (pass_fraction 0.028)**
- By asset class: equity 2/36, **crypto 0/36 (decisive fail)**
- By vol regime: low 0/24, mid 0/24, high 2/24
- Best cell: QQQ, exit_sma_period=20/max_hold_days=10, high-vol regime, Sharpe 1.01 (barely above threshold, single-cell artifact)

## Single-config validators (exit_sma_period=20, max_hold_days=10)

| Symbol | Trades | Sharpe (full) | MDD | TC-survival (net Sharpe) |
|---|---|---|---|---|
| QQQ | 1 | 0.578 **FAIL** (thr 1.0) | 0.021 PASS | 0.569 PASS |
| SPY | 1 | 0.292 **FAIL** (thr 1.0) | 0.035 PASS | 0.284 **FAIL** (thr 0.5) |

## Decision: REJECTED

The monotonic-decline constraint is far too restrictive: only **1 trade**
fires over 7.5 years of daily bars on both QQQ and SPY (vs. TD Sequential
Countdown's already-sparse but more active 10-trade near-miss,
2026-09-08-079). A single trade cannot support a meaningful Sharpe
estimate; full-sample Sharpe misses the threshold decisively on both
symbols. Grid pass_fraction 0.028 (2/72, both in the high-vol tercile only)
is a small-sample artifact, not a real edge. Crypto failed all 36 cells.

Walk-forward and parameter-sensitivity checks were skipped as
uninformative given only 1 trade full-sample -- any split necessarily
contains 0 or 1 trades, making the metric meaningless (documented per
Step 7's guidance to run whichever validator subset is relevant).

This closes out the DeMark TD-family (plain Setup, Sequential Countdown,
Combo Countdown -- 3 variants) for this repo's scope: the countdown phase's
signal frequency scales inversely with its strictness, and TD Combo's
extra monotonic constraint pushes frequency below the minimum viable
sample size for daily-bar QQQ/SPY.

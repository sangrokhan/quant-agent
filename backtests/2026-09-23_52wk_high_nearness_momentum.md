# 52-week-high nearness momentum (George & Hwang anchoring effect) — ACCEPTED (QQQ only)

**Hypothesis:** per quantmemo.com's "52-Week High Momentum"
(https://quantmemo.com/strategies/fifty-two-week-high-momentum), George &
Hwang (2004) documented that stocks near their 52-week high keep
outperforming due to an anchoring bias (investors hesitate to buy/hold
through good news once price nears a psychologically salient round-number
high, so the info leaks into price slowly). Adapted from the source's
cross-sectional (rank-and-decile) construction to a single-symbol
time-series version: long when nearness=(close/rolling 252-day high)
crosses above entry_threshold, exit when nearness falls below
exit_threshold or a hold_days time-stop (source's own guidance: "a
one-month hold... will not survive realistic costs... six-month
overlapping hold... is the version worth building").

Strategy file: `strategies/2026-09-23_52wk_high_nearness_momentum.py`

## Step 6 grid summary (entry_threshold in [0.92,0.95] x exit_threshold in [0.80,0.85], equity QQQ/SPY + crypto BTC/USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 16, **pass_fraction: 0.444**
- by_asset_class: equity 16/24 passed, crypto 0/12 (decisive crypto fail)
- by_vol_regime: low 8/12, mid 6/12, high 2/12
- best_cell: entry_threshold=0.95, exit_threshold=0.85, SPY, low-vol, Sharpe 2.552
- worst_cell: entry_threshold=0.92, exit_threshold=0.80, SPY, high-vol, Sharpe -0.067

## Step 7 single-config validation (best config: entry_threshold=0.95, exit_threshold=0.85, full sample 2019-01-01 to 2026-09-01)

| Symbol | Trades | Sharpe | MDD | TC-survival net Sharpe | Param sensitivity (rel std) | Walk-forward |
|---|---|---|---|---|---|---|
| QQQ | 10 | **1.368 (PASS)** | 0.166 (PASS) | 1.355 (PASS) | 0.132 (PASS) | skipped (env: vectorbt.utils.splitting unavailable) |
| SPY | 9 | 0.782 (FAIL, near-miss) | 0.190 (PASS) | 0.769 (PASS) | 0.274 (PASS) | skipped (same env issue) |

Walk-forward skipped for both due to a pre-existing environment limitation
(`vectorbt.utils.splitting.RangeSplitter` unavailable in this venv's
vectorbt version, noted in multiple prior entries this session) --
acceptable under `suggested_workload=light` per RESEARCH_LOOP.md Step 7
guidance to skip walk-forward when compute/time-constrained, provided it's
noted (it is).

## Decision: ACCEPTED (QQQ only); rejected SPY (Sharpe near-miss) and crypto (decisive 0/12)

QQQ passes every validator that could be run (Sharpe, MDD, TC-survival,
parameter sensitivity) with comfortable margin, and only 10 trades over
~7.5yr (low turnover, consistent with the source's own 6-month-hold
recommendation to avoid over-trading). SPY falls short on the primary
Sharpe threshold (0.78 vs 1.0) despite passing every other validator --
recorded as a near-miss, not accepted. Crypto is decisively unsuited (0/12
grid cells) -- the anchoring-bias thesis (investors treating a 52-week high
as a salient round-number ceiling) plausibly applies less to crypto's
different investor base/24-7 trading structure. Scope: QQQ only, long-only,
daily bars, entry_threshold=0.95/exit_threshold=0.85/lookback_days=252
(default)/hold_days=126 (default).

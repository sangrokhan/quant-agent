# Backtest Report — 2026-09-03_turn_of_month

**Hypothesis:** The turn-of-the-month (TOTM) calendar effect (long only
during the last trading day of the month + first N trading days of the
next month, flat otherwise) captures essentially all of an index's
positive drift, per McConnell & Xu (2008, Financial Analysts Journal,
"Equity Returns at the Turn of the Month") and Ariel (1987).

**Source:** https://tapescript.io/blog/turn-of-the-month-effect. Summarizes
McConnell & Xu (2008): 1926-2005 US equities, essentially all of the
market's average positive return occurred in a 4-trading-day window (last
day of month + first 3 of next month), confirmed across 34 other
countries. Attributed to predictable month-end cash flows (payroll, 401k
contributions, fund rebalancing) -- a mechanism specific to equities, so
crypto (no comparable payroll cycle) is tested as an explicit
falsification check.

**Universe / period:** SPY, QQQ (equity, `load_equity`), BTC/USDT, ETH/USDT
(crypto, `load_crypto`, forced `interval="1d"`), 2019-01-01 to 2026-09-01.

**Signal:** long on the last `days_before_month_end` trading day(s) of a
calendar month and the first `days_after_month_start` trading days of the
next; flat otherwise. Pure calendar rule, no price-based inputs at all --
the first non-price-based signal family tried in this repo. Position
lagged 1 day.

## Step 6 — Grid test (days_before_month_end ∈ {1,2} ×
days_after_month_start ∈ {3,5} × 2 equity + 2 crypto symbols × 3 vol-regime
terciles = 48 cells)

- **Overall pass_fraction: 0.229** (11/48 cells pass Sharpe>=1.0 AND MDD<=25%)
- By asset class: equity 10/24 (42%), crypto 1/24 (4%)
- By vol regime: low 5/16 (31%), mid 6/16 (38%), high 0/16 (0%)
- Best cell: QQQ, days_before=1, days_after=5, low-vol regime, Sharpe 1.92
- Worst cell: BTC/USDT, days_before=2, days_after=3, mid-vol regime, Sharpe -0.14

## Step 7 — Single-config validation (best grid params: days_before=1,
days_after=5), full-sample

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel.std) |
|---|---|---|---|---|
| SPY | 0.98 (FAIL, need >=1.0, narrow miss) | 17.9% (PASS) | 0.58 (PASS) | 0.25 (PASS) |
| QQQ | 0.77 (FAIL) | 21.4% (PASS) | 0.48 (FAIL, need >=0.5) | 0.21 (PASS) |
| BTC/USDT | 0.84 (FAIL) | 37.1% (FAIL, need <=35%) | 0.72 (PASS) | 0.25 (PASS) |

Walk-forward skipped (validator still broken -- `vbt.utils.splitting.RangeSplitter`
missing, tracked since 2026-09-03-002, unfixed again this iteration since
the full-sample Sharpe already fails on all three tested symbols).

## Decision: REJECT (all three tested symbols)

No symbol clears all validators at the grid-optimal parameterization: SPY
narrowly misses the Sharpe threshold (0.98 vs 1.0), QQQ misses both Sharpe
and transaction-cost survival, and BTC/USDT misses both Sharpe and max
drawdown. The literature's headline claim (the 4-day window "captures
essentially all" of the market's average return) does describe *raw
average daily return concentration*, not necessarily a Sharpe>=1.0,
MDD<=35% strategy after the position is actually lagged by 1 day (matching
this repo's no-look-ahead convention) and measured against this repo's
specific hard thresholds -- the effect is real in the source data but its
magnitude here isn't large enough to clear the bar over 2019-2026 once
transaction costs and full-sample Sharpe are applied strictly. The SPY
near-miss (0.98 vs 1.0) is the closest result and could be revisited with
a finer grid (e.g. days_after_month_start swept 2-4, or restricting to
1990-2005-style lower-vol regimes) in a future loop, per RESEARCH_LOOP.md
Step 3's guidance to record near-misses for later refinement rather than
abandoning entirely.

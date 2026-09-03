# Backtest Report — 2026-09-03_bb_meanrev_qqq_volregime

**Hypothesis:** QQQ mean-reverts after closing below its 20-day lower
Bollinger Band, but only in low-volatility regimes (current 20d realized
vol <= trailing 1yr median). High-vol regimes should be excluded because a
prior strategy (2026-09-01-001, SMA crossover) failed specifically due to
regime-dependence around the 2022 rate-hike period.

**Universe / period:** QQQ, daily bars, 2019-01-02 to 2026-09-01 (source:
`data/loaders.py::load_equity`, cache-first via yfinance).

**Signal:** long when `close < SMA20 - 2*STD20` AND `realized_vol_20d <=
median(realized_vol_20d, 252d)`; exit on mean-reversion to SMA20, regime
flip to high-vol, or 10-trading-day max hold.

## Results

| Validator | Result | Value | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio (annualized, freq=D) | -0.30 | >= 1.0 | ❌ FAIL |
| Max drawdown | 15.0% | <= 25% | ✅ pass |
| Transaction cost survival | not run | — | — (skipped, hard-stop at Sharpe) |
| Walk-forward | not run | — | — (skipped, hard-stop at Sharpe) |
| Parameter sensitivity | not run | — | — (skipped, hard-stop at Sharpe) |

Trade count: 14 entries over ~7.7 years. Days in market: 81 / 1927 (~4.2%).
Cumulative strategy return over the full period: **-8.8%** (vs. QQQ
buy-and-hold, which was strongly positive over the same window).

## Interpretation

The core hypothesis is **not supported by this backtest**. The
volatility-regime filter did successfully limit exposure (only 81 days in
market across 7.7 years, keeping max drawdown well within budget at 15%),
but the entry signal itself (lower-Bollinger-Band touch in a low-vol regime)
did not identify a positive-edge mean-reversion opportunity on QQQ daily
bars — the realized Sharpe was negative, meaning the strategy lost money on
a risk-adjusted basis over the sample, not just underperformed a benchmark.

Given the clear Sharpe failure (-0.30 vs the 1.0 threshold, not a
borderline miss), running the remaining validators (transaction costs,
walk-forward, parameter sensitivity) would not change the accept/reject
outcome — a strategy with negative full-sample Sharpe cannot pass a stricter
out-of-sample check. Per `RESEARCH_LOOP.md` Step 5's `suggested_workload`
guidance and Step 6, this is logged as a straightforward **reject** without
spending compute on the remaining checks this loop iteration.

## Notes for future loops

- The mean-reversion premise may still have merit on a *shorter* timeframe
  (intraday/hourly) or a *wider* band (e.g. 2.5-3 std) that trades less
  often but with a stronger edge per trade — 14 trades over 7.7 years is
  thin, and the negative Sharpe could partly reflect noise rather than a
  true negative edge. A future loop could revisit with a coarser
  band/regime threshold sweep instead of abandoning the idea entirely.
- QQQ's strong secular uptrend over 2019-2026 means *any* out-of-market-days
  strategy has a structural headwind vs. buy-and-hold; a fairer read of
  "does mean-reversion work" might isolate return *only* during the days the
  strategy trades and compare that to QQQ's return during the same days,
  rather than judging via portfolio-level annualized Sharpe over the full
  window (which conflates "strategy has an edge" with "strategy is out of a
  rising market most of the time"). Worth a metric refinement in
  `validation/validators.py` for future strategies of this shape.

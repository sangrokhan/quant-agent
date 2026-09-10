# Backtest report: TQQQ/TMF Risk-Mitigation Portfolio with Crash Filter

**Strategy file:** `strategies/2026-09-11_tqqq_tmf_crash_filter_portfolio.py`
**Hypothesis source:** QuantifiedStrategies.com's "Triple Leveraged ETF
Trading Strategy (44% Annual Returns)" (based on Lewis Glenn 2020 paper),
visited this iteration via browser_exec fallback.

## Hypothesis

Hold an equal-dollar 50/50 TQQQ (3x Nasdaq)/TMF (3x 20+yr Treasury)
portfolio, bimonthly rebalanced, exploiting their generally negative
correlation to mitigate TQQQ-alone's severe drawdowns. Crash filter: if
TQQQ drops >=20% in a single day, move 100% to IEF until TQQQ recovers
above its pre-crash price, then resume 50/50. Source's own disclosed
headline stats: CAGR 44.9%, max END-OF-MONTH drawdown 24.5% (vs TQQQ-alone's
49.1%), though the source candidly notes 2022 (stocks AND bonds falling
together) was a period with "no place to hide," and separately discloses
the max DAILY drawdown (not EOM-sampled) was still 42.2%.

## Single-config validation (Step 7) -- decisive rejection before grid test

Full-sample (2015-01-01 to 2026-09-01) test on TQQQ (the paper's own
intended target asset), with the crash-filter mechanism implemented exactly
as disclosed (bimonthly rebalance, -20% single-day trigger, IEF cash-park,
recovery-price re-entry):

| crash_threshold | Sharpe | MDD |
|---|---|---|
| -0.15 | 0.815 | 0.663 |
| -0.20 (source's default) | 0.631 | 0.767 |
| -0.25 | 0.674 | 0.738 |

A sanity-check plain DAILY-rebalanced (no crash filter, no bimonthly drift)
50/50 TQQQ/TMF portfolio was also computed directly: Sharpe 0.717, MDD
0.750 -- confirming the crash filter and bimonthly-rebalance mechanics in
this repo's implementation are not the cause of the failure; the underlying
70%+ drawdown is intrinsic to holding a 3x-leveraged equity ETF at 50%
weight through this backtest's full history (which includes the 2022
stocks-and-bonds-simultaneously-falling regime the source itself flags as
"no place to hide").

- `check_sharpe_ratio`: **FAILED** across all crash_threshold values tested
  (best 0.815 < 1.0).
- `check_max_drawdown`: **FAILED decisively** across all configs (0.66-0.77
  vs 0.25 budget) -- this repo's validator computes max drawdown on the
  DAILY-close cumulative return series, which is a stricter (and more
  standard) measure than the source's own headlined "end-of-month sampled"
  drawdown statistic (EOM sampling can dramatically understate true
  intra-month drawdown depth, especially for a 3x-leveraged, high-volatility
  asset like TQQQ). The source's own separately-disclosed "max DAILY
  drawdown" figure (42.2%) is itself already far above this repo's 0.25
  budget, so even by the source's own more conservative daily-drawdown
  measure, this strategy would not have passed this repo's validator bar.

## Decision: REJECTED (no grid test run -- decisive single-config failure)

Given the decisive Sharpe AND max-drawdown failure on the paper's own
intended target asset (TQQQ) across a 3-value crash_threshold sweep, and
confirmation via an independent from-scratch sanity check that the failure
is intrinsic to the leveraged-ETF exposure itself (not an implementation
bug), this iteration skips the full param-grid/asset-class sweep (workload
budget better spent elsewhere) and logs a decisive rejection directly.

## Notes for future loops

- This is a useful methodological finding for this repo generally: sourced
  strategies that headline an "end-of-month" or otherwise NON-daily-sampled
  drawdown statistic should be treated with extra skepticism when porting
  into this repo's daily-close MDD validator, since EOM/monthly sampling
  can materially understate the true worst intra-period drawdown --
  especially for leveraged/high-volatility instruments. Future loops
  encountering similar "smoothed" headline stats (EOM, weekly-sampled, etc.)
  should flag this explicitly before assuming the source's own numbers will
  translate to a pass on this repo's daily-bar validators.
- Leveraged ETFs (TQQQ/TMF/SOXL/UPRO/etc.) as a category may be worth a
  dedicated feasibility note: their extreme volatility profile makes them
  structurally unlikely to clear this repo's 0.25 MDD budget in almost any
  single-asset or simple-pair construction, absent a much more aggressive
  risk-management overlay (e.g. volatility targeting sized well below 50%
  notional, not just a rare circuit-breaker).

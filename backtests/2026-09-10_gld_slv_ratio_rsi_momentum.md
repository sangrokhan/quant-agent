# Backtest report: GLD/SLV ratio RSI(5) pairs-trade-style long-GLD momentum

**Strategy file:** `strategies/2026-09-10_gld_slv_ratio_rsi_momentum.py`
**Knowledge base id:** 2026-09-10-047
**Outcome: REJECTED** (decisive Sharpe fail across the full parameter grid)

## Hypothesis

Per quantifiedstrategies.com's Gold/Silver Chart Ratio Strategy article
(visited this iteration, https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/):
the source's own disclosed rule is a direct pairs trade using a 5-day RSI
of the GLD/SLV ratio -- buy GLD when the ratio's 5-day RSI closes above 75,
exit when RSI falls below 50. Source explicitly notes its own pair-trade
equity curve "shows a flat development" (a weak result by the source's own
admission), which this iteration tested independently rather than assuming
failure. Approximated as a single-leg long-only GLD trade (no short SLV
leg, consistent with the repo's convention for other pairs-trade
adaptations). Distinct from this repo's existing GLD/SLV ratio z-score
REGIME GATE (2026-09-05-030, which gates a different primary asset).

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = rsi_window∈{3,5,10} ×
entry_threshold∈{70,75,80} × exit_threshold∈{40,50}, symbols = {equity:
GLD only -- this is a single-instrument RSI-of-ratio momentum strategy, not
a cross-asset trend gate, so no crypto/BTC applicability}, vol_regime_splits=3,
2018-01-01 to 2024-12-31.

- **total_cells:** 54
- **passed_cells:** 12
- **pass_fraction:** 0.222
- **by_vol_regime:** low 8/18, mid 1/18, high 3/18
- **best_cell:** rsi_window=3, entry_threshold=80, exit_threshold=50, low-vol tercile, Sharpe=2.072 (single favorable slice)

## Full-sample single-config sweep

| rsi_window | entry | exit | GLD Sharpe | GLD MDD |
|---|---|---|---|---|
| 5 | 75 | 40 | 0.845 | 0.125 |
| 5 | 70 | 40 | 0.820 | 0.136 |
| 10 | 70 | 40 | 0.810 | 0.100 |
| 5 | 70 | 50 | 0.798 | 0.181 |

**Best full-sample config (rsi_window=5, entry_threshold=75,
exit_threshold=40): GLD Sharpe=0.845** — matches the source's own default
parameters closely (5-day RSI, ~75 entry threshold) but decisively below
the 1.0 threshold, consistent with the source's own admission that its
pair-trade equity curve "shows a flat development." No parameter
combination in the swept grid clears 1.0.

## Decision

**Rejected — decisive, consistent with source's own disclosed weak
result.** The source itself flagged this exact construction as
underwhelming, and this repo's independent backtest confirms it: best
full-sample Sharpe 0.845, no config close to the 1.0 threshold. Single-
instrument, equity-only (no meaningful crypto analogue for this
metals-ratio construction).

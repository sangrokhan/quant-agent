# Backtest Report: Cumulative Mispricing Index (CMPI) Copula Pairs Trade

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_cmpi_copula_pairs_meanrev.py`
**Status:** REJECTED

## Hypothesis

Per Hudson & Thames' "Copula for Pairs Trading" (Strategy 2 section,
https://hudsonthames.org/copula-for-pairs-trading-overview-of-common-strategies/,
read via browser_exec). Cumulative Mispricing Index (CMPI): daily
Mispricing Index MPI_t = Gaussian-copula conditional probability of one
leg's return given the other leg's return; CMPI_t = CMPI_{t-1} + (MPI_t -
0.5), cumulated while a position is open, reset to 0 after each close.
Rad et al (2016)'s variation implemented: AND-logic open (CMPI_A <=
-open_threshold AND CMPI_B >= +open_threshold), OR-logic exit (CMPI_A
returns to >= 0, OR stop-loss, OR time-stop), no reset while in position.
QQQ/SPY equity pair + BTC/USDT vs ETH/USDT crypto pair, distinct
construction from this same cron trigger's earlier Strategy-1 copula entry
(2026-09-28-030, rejected) despite sharing the copula-fitting machinery.

## Grid test summary (Step 6)

`param_grid`: cmpi_open_threshold in [1.0, 2.0, 3.0] (stop = 2x open) x
max_hold_days in [20, 40]; symbols equity=[QQQ,SPY], crypto=[BTC/USDT,
ETH/USDT]; vol_regime_splits=3.

- total_cells: 72
- passed_cells: 0
- pass_fraction: 0.0
- **72/72 cells returned "empty/no-trade slice"** -- the strategy essentially
  never opens a position at ANY tested threshold >= 1.0.

## Root-cause diagnostic (not a grid parameter, structural)

Inspecting the raw CMPI series directly (QQQ/SPY, rank_window=60): CMPI_A
(QQQ) drifted from 0 to a mean of +5.2 (range -0.9 to +13.3) and CMPI_B
(SPY) drifted from 0 to a mean of -9.8 (range -20.7 to +0.8) over a ~4.5-
year sample, i.e. BOTH legs' cumulative mispricing indices trend
persistently in ONE direction rather than mean-reverting/oscillating
around 0 as the AND-open logic requires (needs CMPI_A very negative AND
CMPI_B very positive SIMULTANEOUSLY). Lowering the threshold to 0.3
(QQQ-only) produced only 5 trades total over the whole sample (Sharpe
-0.572); thresholds >= 0.5 produced zero trades. This is not a
mistuned-parameter problem -- it reproduces, empirically, exactly the
convergence failure mode the source article itself warns about in its
"Comments" section: "this type of strategy ... is betting on the mean-
reversion of CMPIs, but they behave more like martingales," meaning the
raw cumulative-sum construction is fundamentally non-stationary for this
symbol pair/sample and does not generate tradeable AND-logic
opportunities at any reasonable threshold.

## Decision: REJECT

No config produces a tradeable signal (near-zero trade count across the
entire grid); this is a structural failure of the CMPI construction on
this data (drift/martingale behavior), not a parameter-tuning issue.
Single-config validators (Step 7) were not run since there is no non-empty
config to validate. Strategy file retained in `strategies/` as a
rejected-attempt record per Step 8's guidance.

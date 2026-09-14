# ZigZag Trend-Maturity Continuous Sizing Overlay — Backtest Report

**Date:** 2026-09-14
**Strategy ID:** 2026-09-14-156 (assigned in knowledge_base log)
**File:** `strategies/2026-09-14_zigzag_maturity_sizing_sma_trend.py`

## Hypothesis

ZigZag indicator (per Google AI-overview cross-referencing
Investopedia/LuxAlgo/NAGA/Angel One): a repainting-safe construction that
only confirms a new swing pivot once price reverses from the running
extreme by a threshold percentage (`pct_change = (current - prev_swing) /
prev_swing * 100`). Repo has 6 prior ZigZag entries, ALL binary
breakout/pattern triggers off confirmed pivots (mostly rejected). This
iteration reframes ZigZag's underlying continuous quantity — the signed %
distance of current close from the last CONFIRMED swing pivot ("trend
maturity") — as a CONTINUOUS SIZING dial: rolling z-scored + tanh-squashed
to [-1,+1], sized within an SMA(trend_window) uptrend gate. Rationale: a
larger confirmed move since the last swing low signals more momentum/
conviction in the current up-leg, warranting larger exposure. First ZigZag
continuous-sizing variant.

Source: Google AI-overview at
https://www.google.com/search?q=Zig+Zag+indicator+formula+trading+strategy+percentage+reversal
(via browser_exec fallback — web_search's DuckDuckGo backend failed for
this query with a TLS connection error), cross-referencing
Investopedia/LuxAlgo/NAGA/Angel One summaries shown inline.

## Implementation note (bug caught and fixed pre-grid-test)

First implementation of the confirmed-pivot state machine had a bug: the
"undetermined initial leg" branch let `running_extreme` always equal the
current price, so the reversal test against `running_extreme` could never
trigger — the pivot direction was permanently stuck undetermined. Caught
via a parameter-sensitivity smoke test showing IDENTICAL Sharpe across all
three `zigzag_deviation_pct` grid values (a dead giveaway the parameter
wasn't doing anything). Fixed by testing the initial leg's breach against
the fixed starting price `vals[0]` instead of the still-moving
`running_extreme`. Re-verified the fix produces different `pct_from_pivot`
series (and different Sharpes) per deviation_pct before re-running the grid.

## Grid test summary (Step 6)

`param_grid={zigzag_deviation_pct: [3.0,5.0,8.0], sensitivity: [0.5,0.7]}`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.

- **total_cells:** 72, **passed:** 27, **pass_fraction:** 0.375.
- **by_asset_class:** equity 16/36 (0.444), crypto 11/36 (0.306).
- **by_vol_regime:** low 20/24 (0.833), mid 7/24 (0.292), high 0/24 (0.0) —
  this overlay decisively fails in high-vol terciles across the board.
- **best_cell:** QQQ, zigzag_deviation_pct=5.0/sensitivity=0.5, low-vol,
  Sharpe 2.54.
- **worst_cell:** QQQ, zigzag_deviation_pct=3.0/sensitivity=0.7, high-vol,
  Sharpe -0.47.

## Single-config validator results (Step 7)

Best grid config (zigzag_deviation_pct=5.0, sensitivity=0.5) tested per
symbol, leverage_cap=1.0 (equity) / 0.4 (crypto):

| Symbol | Trades | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | 104 | 1.402 (pass) | 0.098 (pass) | 1.113 (pass) | 0.75 (pass) | 0.225 (pass) | **accepted** |
| SPY | 118 | 0.874 (**fail**, thr 1.0, near-miss) | 0.079 (pass) | 0.526 (pass) | 0.75 (pass) | 0.095 (pass) | **rejected** |
| BTC/USDT | 205 | 1.237 (pass) | 0.225 (pass) | 0.917 (pass) | 1.0 (pass) | 0.066 (pass) | **accepted** |
| ETH/USDT | 257 | 1.163 (pass) | 0.228 (pass) | 0.880 (pass) | 1.0 (pass) | 0.022 (pass) | **accepted** |

## Decision

**Accepted (QQQ, BTC/USDT, ETH/USDT):** all 5 validators pass.
**Rejected (SPY):** genuine near-miss on gross Sharpe alone (0.874 vs 1.0
threshold); MDD, TC-survival, walk-forward, and parameter sensitivity all
pass cleanly.

Scope note: this ZigZag trend-maturity continuous-sizing dial degrades
sharply in high-vol regimes (0/24 grid cells pass) — treat it as a
low/mid-vol-regime overlay only for QQQ/BTC/ETH; do not deploy through a
high-vol stretch without an explicit vol-regime kill-switch.

Full raw grid: `/tmp/zigzag_grid_summary.json` (not committed, ephemeral).
Full raw validators: `validators_zigzag_maturity_sizing.json`.

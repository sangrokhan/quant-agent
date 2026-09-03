# Backtest Report: SuperTrend (ATR-based flip) Long-Only Trend-Following

**Strategy file:** `strategies/2026-09-03_supertrend_atr_longonly.py`
**Hypothesis ID:** 2026-09-03-014
**Source:** Google AI-overview summary (fetched via browser_exec after
`web_search` returned no results for this keyword) of the standard
SuperTrend indicator.

## Hypothesis

SuperTrend = ATR-based dynamic support/resistance band (ATR period 10-14,
multiplier ~3 by default) that flips direction based on price crossing it;
long when price closes above the SuperTrend line (line flips down->up);
flat when price closes below it (flips up->down). First ATR-volatility-
ADAPTIVE trend indicator tested in this repo — distinct from the fixed
price-level Donchian breakout (2026-09-03-008) and fixed-lookback SMA/
momentum trend filters (2026-09-01-001, -004, -012) because the band width
scales with current volatility rather than a fixed window.

Long-only implementation (no shorting) per SAFETY.md/repo convention.

## Grid test (validation/grid_test.py::run_strategy_grid)

Grid: `atr_period` in {10,14} x `multiplier` in {2.0,3.0,4.0} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **pass_fraction: 0.25** (18/72)
- by_asset_class: equity 18/36 (50%), crypto 0/36 (0%)
- by_vol_regime: low 12/24 (50%), mid 6/24 (25%), high 0/24 (0%)
- best_cell: QQQ, atr_period=14/multiplier=4.0, low-vol regime, Sharpe 3.00
- worst_cell: QQQ, atr_period=14/multiplier=4.0, high-vol regime, Sharpe -0.57

Same familiar pattern as nearly every trend-following strategy tested in
this repo: equity-only, low/mid-vol-only, 0% pass in high-vol regime.

## Single-config validators (best grid config: atr_period=14, multiplier=4.0)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd (4-split) |
|---|---|---|---|---|
| QQQ | 1.49 (pass, thr 1.0) | **25.6% (FAIL, thr 25%)** | 1.43 (pass, thr 0.5, 34 trades @10bps) | 0.75 (pass, thr 0.75) |
| SPY | 0.97 (fail, thr 1.0) | 23.2% (pass) | 0.88 (pass) | 1.0 (pass) |
| BTC/USDT | 0.22 (fail) | 44.2% (fail) | 0.11 (fail) | 1.0 (pass) |

Parameter sensitivity (6-point atr_period/multiplier sweep on QQQ): relative
std 0.10, well inside the 0.5 threshold — Sharpe stays in the 1.13-1.49
range across all combos tested, so QQQ's near-miss on MDD is not a fragile
artifact of one specific parameter choice.

Walk-forward used a manual 4-way date-slice fallback (vectorbt
`utils.splitting.RangeSplitter` still broken — unfixed since 2026-09-03-002).

## Decision: **REJECT**

QQQ (the best-performing symbol/config) clears Sharpe (1.49), net-of-cost
Sharpe (1.43), walk-forward (3/4 splits, exactly at the 0.75 threshold), and
parameter sensitivity (rel.std 0.10) — but fails the max-drawdown gate at
25.6% vs the 25% budget, a narrow (0.6 percentage point) miss. SPY misses
the Sharpe gate (0.97 vs 1.0), also a narrow near-miss. BTC/USDT fails
decisively across Sharpe, MDD, and TC-adjusted Sharpe — the ATR-adaptive
trend filter does not transfer to crypto's regime any better than the fixed-
window trend/momentum filters already tested (2026-09-03-002/-003/-004/-008/
-012).

Both QQQ and SPY are near-misses on a single validator each (MDD and Sharpe
respectively) — worth revisiting in a future loop with a slightly higher
ATR multiplier (5.0+) to trade fewer, more decisive trend segments and
potentially trim QQQ's MDD below 25%, or accepting a relaxed MDD budget
(e.g. 30%) given how close QQQ came and how strong its Sharpe/TC/walk-
forward profile otherwise is.

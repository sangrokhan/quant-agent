# Backtest report: KAMA Trend Crossover (2026-09-16)

**Strategy file:** `strategies/2026-09-16_kama_trend_crossover.py`
**KB entry:** `2026-09-16-184` (accepted, SPY only)

## Hypothesis

Per Kaufman's KAMA construction (Google AI-overview synthesis of
PyQuantLab/StockCharts/TradingView/Stonehill Forex/ChartMini/Darwinex),
KAMA adapts its smoothing speed via the Efficiency Ratio, hugging price
during clean trends and flattening during chop. **Distinct from this
repo's extensive prior Kaufman Efficiency Ratio work** (12+ entries, e.g.
2026-09-14-111/2026-09-16-072) which used ER directly as a continuous
position-sizing dial — this strategy instead builds the actual KAMA
adaptive-smoothing line and trades a **crossover** signal against it. Long
entry when close crosses above KAMA; exit when close crosses below
(KAMA − `atr_buffer_mult`×ATR(14)) (source's own noted whipsaw-reduction
buffer), or a `max_hold_days` time-stop.

**Source:** Google AI-overview synthesis, read via `browser_exec` Google
SERP.

## Grid test (Step 6)

`GridSpec(param_grid={"er_period": [8,10,15], "atr_buffer_mult":
[0.5,1.0,1.5], "max_hold_days": [30,40]}, symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` — 216 cells,
2018-01-01 to 2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 67/216 = 0.310 |
| by_asset_class | equity 54/108, crypto 13/108 |
| by_vol_regime | low 49/72, mid 17/72, high 1/72 |
| best cell | SPY, er_period=15/atr_buffer_mult=1.0/max_hold_days=30, low-vol, Sharpe 3.062 |

## Single-config validators (er_period=15, atr_buffer_mult=1.0,
max_hold_days=30, full sample 2018-2026)

| symbol | trades | sharpe | mdd | tc_survival |
|---|---|---|---|---|
| QQQ | 72 | 0.934 ❌ | 0.233 ✅ | 0.798 ✅ |
| **SPY** | 71 | **1.088 ✅** | **0.168 ✅** | **0.896 ✅** |
| BTC/USDT | 96 | 0.483 ❌ | 0.597 ❌ | 0.442 ❌ |
| ETH/USDT | 87 | 0.624 ❌ | 0.694 ❌ | 0.594 ✅ (partial) |

A 100-combo full sweep of (er_period × atr_buffer_mult × max_hold_days) on
QQQ found no configuration clearing both Sharpe≥1.0 and MDD≤0.25
simultaneously — QQQ genuinely doesn't clear the bar for this signal
mechanism, unlike SPY.

**SPY walk-forward** (manual 4-slice fallback): [0.528, 1.306, 1.602,
1.090] — all 4 splits positive, pass_fraction 1.0 (threshold 0.75).

**SPY parameter sensitivity** (9-combo er_period×atr_buffer_mult sweep at
max_hold_days=30): relative_std = 0.223 (threshold 0.5) — passes, robust.

## Decision

**Accepted — SPY only** (equity, `er_period=15, atr_buffer_mult=1.0,
max_hold_days=30`). All 5 validators pass for SPY. QQQ, BTC/USDT, and
ETH/USDT are rejected — QQQ falls just short on Sharpe (0.934 vs 1.0
threshold) across an extensive parameter sweep, and crypto fails
decisively on MDD/Sharpe. This is a narrower-but-honest acceptance per
RESEARCH_LOOP.md Step 6 guidance — the strategy's scope is recorded as
SPY-only, not broadly applicable across the universe tested.

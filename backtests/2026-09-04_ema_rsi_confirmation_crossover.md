# 2026-09-04 EMA(20/50) Crossover + RSI(14)>50 Confirmation — Backtest Report

**Hypothesis** (id `2026-09-04-165`): A classic dual-EMA trend crossover
(fast EMA(20) flipping above slow EMA(50)) is a higher-conviction long
entry when confirmed by RSI(14) staying above its 50 midline at the
crossover bar. Exit on the reverse EMA cross, RSI dropping below 50, or a
max_hold_days time-stop. Per a widely-circulated "Uptrend trading strategy
using EMA and RSI confirmation" rule snippet.

**Source**: Google search snippet of a Facebook post ("Ocious Wagner") --
concrete numeric rule captured directly from the search result (20/50 EMA
cross + RSI(14)>50), original post itself not independently verified beyond
the snippet.

**Strategy**: `strategies/2026-09-04_ema_rsi_confirmation_crossover.py`

## Grid test (fast_span∈{10,20}, slow_span∈{50,100}, max_hold_days∈{15,20}; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3)

- total_cells: 96, passed_cells: 23, **pass_fraction: 24.0%**
- by_asset_class: equity 23/48 passed; crypto 0/48 (decisive rejection)
- by_vol_regime: low 13/32, mid 9/32, high 1/32
- best_cell: QQQ fast_span=20/slow_span=50/max_hold_days=20, low-vol, Sharpe 2.55

## Single-config validation, full sample 2019-2026 (fast_span=20, slow_span=50, max_hold_days=20)

| Symbol | Sharpe | Passed | MDD | Passed | TC-survival | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 0.930 | NO (near-miss) | 0.094 | YES | 0.873 (42 trades) | 0.124 (pass) |
| SPY | 0.208 | NO (decisive) | 0.144 | YES | 0.152 (30 trades) | 0.340 (pass) |

QQQ is a near-miss (0.930 vs 1.0 threshold, off by 0.07). SPY fails
decisively (0.208), a clear miss not a near-miss -- the RSI>50 confirmation
gate on top of the EMA cross does not generalize across both equity
symbols despite the promising grid pass_fraction. Crypto 0/48 grid cells,
decisively rejected.

## Decision: REJECTED

QQQ near-miss but SPY's decisive failure rules out treating this as a
broadly-tested equity edge; per RESEARCH_LOOP.md convention, only clean
passes on the primary config are accepted, and one symbol failing
decisively (not near-miss) means the combined rule doesn't hold. Logged as
a near-miss on QQQ specifically for a future loop that might narrow scope
to QQQ-only or retune the RSI midline/EMA windows.

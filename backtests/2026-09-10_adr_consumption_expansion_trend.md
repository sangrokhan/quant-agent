# Backtest report: ADR consumption range-expansion trend continuation

**Strategy file:** `strategies/2026-09-10_adr_consumption_expansion_trend.py`
**Knowledge base id:** 2026-09-10-043
**Outcome: ACCEPTED (QQQ, SPY only — equity; crypto rejected/no edge)**

## Hypothesis

Per audacity.capital's Average Daily Range guide (visited this iteration,
https://audacity.capital/trading-guides/average-daily-range): "ADR
consumed" (today's high-low range / trailing average range) is a context
filter, and the source's own explicit guidance is that a day consuming well
beyond 100% of its historical ADR, backed by trend, should NOT be faded —
it signals genuine range expansion / trend continuation rather than
exhaustion. Operationalized as a daily-bar swing strategy: bullish day
(close>open) with today's range >= expansion_threshold x its trailing ADR,
gated by an SMA trend filter, is a long entry; exit on trend break or a
time-stop. Distinct from the previously-tested NR7 contraction-precedes-
expansion pattern (2026-09-04-081), DeMark Range Expansion Index
(2026-09-06-167), and single-bar Volatility-Ratio breakout (2026-09-07-019).

## Grid test summary (Step 6)

`run_strategy_grid`, param_grid = adr_window∈{10,14,20} ×
expansion_threshold∈{1.2,1.3,1.5} × trend_window∈{50,100} ×
max_hold_days∈{10,15}, symbols = {equity: QQQ/SPY, crypto:
BTC/USDT/ETH/USDT}, vol_regime_splits=3, 2018-01-01 to 2024-12-31.

- **total_cells:** 432
- **passed_cells:** 112
- **pass_fraction:** 0.259
- **by_asset_class:** equity 112/216 passed; **crypto 0/216 (decisive fail)** — ADR-consumption expansion-day continuation has no edge on 24/7 crypto markets in this sample (no discrete session-open/close range dynamic the same way equities have)
- **by_vol_regime:** low 65/144, mid 30/144, high 17/144 (works best in calmer regimes but still contributes in mid/high)
- **best_cell:** adr_window=14, expansion_threshold=1.2, trend_window=50, max_hold_days=15, SPY, low-vol tercile, Sharpe=3.078

Best full-sample config across the parameter sweep (adr_window=14,
expansion_threshold=1.2, trend_window=50, max_hold_days=15): QQQ
Sharpe=1.585, SPY Sharpe=1.417 — this is the primary config carried into
Step 7 single-config validation below.

## Full-sample single-config validation (Step 7)

Config: `adr_window=14, expansion_threshold=1.2, trend_window=50, max_hold_days=15`

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | **1.585 ✅** | **1.417 ✅** | ≥1.0 |
| Max drawdown | **0.123 ✅** | **0.088 ✅** | ≤0.25 |
| Transaction cost survival (10bps/trade, 59/64 trades) | **1.447 ✅** | **1.228 ✅** | ≥0.5 net Sharpe |
| Walk-forward (manual 4-way range-split; validators.py's `check_walk_forward` raises on installed vectorbt 1.1.0, pre-existing bug flagged in 2026-09-10-021/022) | **4/4 splits positive, 1.0 ✅** | **3/4 splits positive, 0.75 ✅ (marginal)** | ≥0.75 |
| Parameter sensitivity (expansion_threshold swept 1.1-1.5) | **0.188 relative std ✅** | **0.349 relative std ✅** | ≤0.5 |

All validators pass for both QQQ and SPY. SPY's walk-forward is marginal
(exactly at the 0.75 threshold, one of four splits negative) — worth
flagging for a future loop's near-miss/robustness recheck, but it passes
as specified.

## Decision

**ACCEPTED for equity (QQQ, SPY) only.** Crypto (BTC/ETH) showed zero
edge (0/216 grid cells) and is explicitly NOT part of this strategy's
validated scope — a future loop should not assume this strategy applies to
crypto. SPY's walk-forward passed only marginally (3/4 splits, exactly at
threshold), so treat as accepted-but-worth-monitoring rather than a
decisive slam-dunk on SPY specifically; QQQ's walk-forward was decisive
(4/4 splits positive).

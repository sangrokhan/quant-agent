# Backtest Report: Donchian+Keltner OR-Breakout, Never-Lowered Trailing Stop (2026-09-26)

**Strategy file:** `strategies/2026-09-26_donchian_keltner_breakout_never_lower_stop.py`
**KB id:** 2026-09-26-011

## Hypothesis

Per QuantifiedStrategies.com's summary of Zarattini & Antonacci's "A
Century of Profitable Industry Trends"
(https://quantifiedstrategies.substack.com/p/a-trend-following-strategy-18-annually,
free/fully-disclosed rule): long entry on EITHER a Donchian Channel
breakout (close > rolling 20-day high) OR a Keltner Channel breakout
(close > 20-day EMA + 1.4x ATR); exit via a trailing stop set at the
HIGHER of the 40-day-lookback lower Donchian band and lower Keltner band,
which is NEVER LOWERED once set (only ratchets up). Source's own
century-long cross-sectional/vol-targeted backtest across 48 industries:
18.2% annualized, Sharpe 1.39, MDD 33% vs market 84%. Adapted here to a
single-symbol long-only implementation (no cross-sectional vol-targeted
sizing overlay — out of scope for this repo's per-symbol backtest
framework); the dual-channel OR-entry + max-of-both never-lowered trailing
stop mechanic is tested exactly as disclosed. First strategy in this repo
combining Donchian AND Keltner breakouts this way.

## Grid test (Step 6)

`entry_window` in {15, 20, 30} x `stop_window` in {30, 40, 55}, QQQ/SPY +
BTC/USDT/ETH/USDT, vol_regime_splits=3, 2016-2026 (108 cells):

- **pass_fraction = 0.269 (29/108)**
- by_asset_class: equity 27/54, crypto 2/54
- by_vol_regime: low 20/36, mid 9/36, high 0/36 (trend-following breakout
  edge concentrated in calmer regimes, consistent with whipsaw risk in
  high-vol periods)
- best_cell: `entry_window=15, stop_window=30`, QQQ, low-vol, Sharpe 2.327
- worst_cell: `entry_window=20, stop_window=30`, QQQ, high-vol, Sharpe -0.208

## Single-config validation (Step 7)

Local search around the grid-best region found `entry_window=30,
stop_window=30` clears every threshold on QQQ (grid's own best cell,
`entry_window=15`, narrowly failed max_drawdown at 0.269 vs 0.25 — a wider
entry window trades less often and drew down less).

| Metric | QQQ (ew=30, sw=30) | SPY (same config) |
|---|---|---|
| Sharpe | **1.050** (pass, ≥1.0) | 0.751 (**fail**, <1.0) |
| Max Drawdown | 0.208 (pass, ≤0.25) | 0.167 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 1.009 (pass, ≥0.5) | 0.690 (pass, ≥0.5) |
| Walk-forward (manual 4-split) | 1.0 (pass, ≥0.75) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std, 9-cell) | 0.026 (pass, ≤0.5) | 0.078 (pass, ≤0.5) |
| num_trades | 39 | 45 |

## Decision

**ACCEPT for QQQ only** (all 5 validators pass, and Sharpe/param-sensitivity
are notably robust — rel. std 0.026 across the 9-cell local grid, the
tightest parameter-sensitivity margin of any strategy accepted this cron
trigger). **REJECT for SPY** (consistent near-miss across the entire local
grid, Sharpe capped around 0.72-0.89 depending on parameters — everything
else passes cleanly). Crypto grid pass rate (2/54) too weak to warrant
single-config validation.

## Source

https://quantifiedstrategies.substack.com/p/a-trend-following-strategy-18-annually
(free, fully disclosed rule) — read via `browser_exec` (page content fetched
directly, no paywall on the trading-rules section, unlike most other
QuantifiedStrategies articles visited this cron trigger).

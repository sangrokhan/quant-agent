# Backtest Report: Jump-Diffusion Momentum

**Strategy file:** `strategies/2026-09-26_jump_diffusion_momentum.py`
**KB id:** 2026-09-26-068
**Outcome:** REJECTED (decisive)

## Hypothesis

Source: PyQuantLab's disclosed backtrader `JumpDiffusionMomentumStrategy`
(https://github.com/shortthirdman/TradingStrategies/tree/main/pyquantlab/jump_diffusion_momentum,
read via `browser_exec` after the linked Medium article page 404'd — the
GitHub repo carries the actual source code). Long-only adaptation:

1. `jump_signal = tanh(z-score(return, 20d vol) / jump_threshold)` — return
   jump detector, bounded [-1,1].
2. `momentum_direction` — fraction of positive/negative return days over a
   5-day window, direction set only if the majority fraction clears
   `momentum_threshold`.
3. `TrendVolatilityFilter` — BOTH ADX and ATR must be "sustained rising"
   over a 7-bar lookback (a genuine volatility/trend EXPANSION gate,
   distinct from every static ADX/ATR threshold already in this KB).
4. Entry: `jump_signal > jump_entry_level` AND (momentum confirms OR
   diffusion_trend term) AND both expansion filters pass. Exit: minimum
   hold, then trailing-stop/hard-stop/time-stop.

Distinct from this repo's existing Jump-Weighted Momentum (2026-09-08-151,
a formation-window return-reweighting scheme with no z-score detector or
ADX/ATR gate).

## Grid summary (Step 6)

`param_grid={jump_entry_level:[0.5,0.6,0.7], min_adx_level:[15,20]}`,
symbols equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
72 total cells.

| Metric | Value |
|---|---|
| pass_fraction | 0.125 (9/72) |
| by_asset_class | equity 3/36, crypto 6/36 |
| by_vol_regime | low 0/24, **mid 9/24**, high 0/24 |
| best_cell | BTC/USDT, jump_entry_level=0.5, min_adx_level=15, mid-vol tercile, Sharpe 1.53 |

All passing cells fall in the mid-vol tercile — an unusually narrow single-
regime concentration.

## Single-config validation (Step 7) — best cell, full sample, BTC/USDT

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.120 | ≥ 1.0 |
| Max drawdown | **FAIL** | 0.579 | ≤ 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.050 (662 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken, per established repo workaround) | PASS | 3/4 splits positive (0.75) | ≥ 0.75 |

Crypto's higher volatility trips the jump-detector far more often (662
trades vs an equity-only smoke test of ~29 trades over 11 years), and the
resulting high turnover destroys both Sharpe and cost-survival despite the
mid-vol-tercile grid cell's promising Sharpe of 1.53 — another instance of
this KB's recurring pattern where a narrow single-regime grid pass does not
generalize to the full sample.

## Decision

**Reject (decisive).** Strategy file retained in `strategies/` as a
rejected-attempt record (not live).

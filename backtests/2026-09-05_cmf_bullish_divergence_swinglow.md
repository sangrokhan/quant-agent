# CMF Bullish Divergence at Swing Lows — Backtest Report

**Date:** 2026-09-05
**Strategy file:** `strategies/2026-09-05_cmf_bullish_divergence_swinglow.py`
**Knowledge base id:** 2026-09-05-047

## Hypothesis

Per TradingView's own Chaikin Money Flow documentation
(tradingview.com/scripts/chaikin_money_flow/): "A bullish CMF divergence
occurs when the price makes a lower low, but the CMF makes a higher low
(suggesting increasing buying pressure)." Implemented as: detect
confirmed swing lows in close (+/- `pivot_window` bars), compare
consecutive swing lows within `lookback_bars`; if price makes a lower
low while CMF(20) makes a higher low, and RSI(14) is still below
`rsi_gate` (avoid buying into an already-overbought bounce), enter long.
Exit on a failed bounce below the swing-low's close, CMF turning
negative, or a `max_hold_days` time-stop. First divergence-based CMF
variant in this repo (distinct from 2026-09-04-043's plain
threshold-cross and 2026-09-05-002's Twiggs Money Flow zero-cross
pullback).

Source: https://www.tradingview.com/scripts/chaikin_money_flow/ (fetched
via `browser_exec` directly — page loaded fine, no fallback needed).
Exact swing-detection/lookback parameters are our own reconstruction
(the source states the divergence concept, not specific numeric rules).

## Grid test summary (Step 6)

`validation/grid_test.py::run_strategy_grid`, param grid
`pivot_window=[4,5,7] x lookback_bars=[40,60,90] x rsi_gate=[55,60,70]`,
symbols `equity=[QQQ,SPY]`, `crypto=[BTC/USDT,ETH/USDT]`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01. **324 cells total.**

- **pass_fraction: 0.0278** (9 / 324 cells)
- by_asset_class: equity 9/162; **crypto 0/162** (rejected outright)
- by_vol_regime: **low 9/108**; mid 0/108; high 0/108 (only works in calm markets)
- best_cell: `pivot_window=4, lookback_bars=40, rsi_gate=60.0`, SPY, low-vol tercile, Sharpe 1.56
- worst_cell: `pivot_window=7, lookback_bars=90, rsi_gate=60.0`, QQQ, high-vol tercile, Sharpe -1.68

## Single-config validation (Step 7) — best config, SPY, full period 2019-2026

Config: `pivot_window=4, lookback_bars=40, rsi_gate=60.0` over the full period (not just the low-vol tercile slice).

| Validator | Result | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ FAIL | -0.17 | >= 1.0 |
| max_drawdown | ✅ pass | 0.158 | <= 0.25 |
| transaction_cost_survival (10bps/trade, 14 trades) | ❌ FAIL | -0.22 | >= 0.5 |
| walk_forward (manual 4-equal-slice fallback) | ❌ FAIL | 2/4 splits positive | >= 0.75 |

## Decision: **REJECTED**

Same narrow-slice pattern as the prior iteration's Decycler strategy:
grid's best isolated low-vol cell (Sharpe 1.56) does not survive when the
same config is applied over the full period (Sharpe -0.17, net-negative
after costs). Signal is too infrequent (9-14 trades over 7.5 years) to
draw a robust conclusion either way, but as tested it fails decisively.
Crypto rejected in every single cell (0/162).

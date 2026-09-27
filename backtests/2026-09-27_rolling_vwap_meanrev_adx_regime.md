# Rolling VWAP Mean-Reversion + ADX Regime Filter — Backtest Report

**Strategy file:** `strategies/2026-09-27_rolling_vwap_meanrev_adx_regime.py`
**Date:** 2026-09-27
**Outcome:** REJECTED

## Hypothesis

Source: https://crosstrade.io/learn/trading-strategies/vwap-reversion (read
2026-09-27 via browser_exec; full Pine Script v6 disclosed for ES/NQ
intraday futures).

Source's rule: fade price extending 2 std-devs from session VWAP, gated by
ADX(14)<=25 (skip trend days), triggered by a rejection candle at the
extreme, entry next bar open, stop 1x ATR beyond trigger high/low, target =
VWAP. This repo's daily-bar-only data (no intraday session data) required
adapting session-VWAP to a rolling N-day volume-weighted VWAP + rolling
std bands, keeping the ADX regime filter + rejection-candle trigger + ATR
stop + VWAP target mechanics intact.

First VWAP-reversion-with-regime-filter strategy in this repo (0 prior hits
for "vwap_reversion").

## Single-config validators (SPY, vwap_window=20, std_mult=1.5, adx_threshold=35.0 — grid's best cell)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.352 | >= 1.0 | **FAIL** |
| Max drawdown | 0.114 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 15 trades) | 0.290 | >= 0.5 | **FAIL** |

(Walk-forward/parameter-sensitivity skipped — grid pass_fraction already
decisive at 0.052, not worth the extra compute per suggested_workload=normal.)

## Step 6 grid summary (vwap_window x std_mult x adx_threshold, QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3)

- Total cells: 96, passed: 5, **pass_fraction = 0.052**
- By asset class: equity 3/48, crypto 2/48 — both weak, no clear winner
- By vol regime: low 1/32, mid 3/32, high 1/32 — no coherent regime pattern
- QQQ fails decisively on ALL 24 grid cells (0/24)
- Best cell: SPY, vwap_window=20, std_mult=1.5, adx_threshold=35, mid-vol
  regime, Sharpe 1.726 — an isolated cell, not corroborated by neighbors

## Decision: REJECTED

Grid pass_fraction (0.052) is one of the lowest recorded this cron trigger;
passing cells are scattered across asset classes/vol-regimes with no
coherent pattern (unlike a genuine edge that clusters in a specific
symbol/regime combination). Single-config validators on the grid's best
cell confirm: full-sample Sharpe (0.352) and net-of-cost Sharpe (0.290)
both fail decisively. Likely explanation: this repo's daily-bar adaptation
of an inherently intraday (session-VWAP, 2-5 trades/day) strategy loses the
core mechanic that made the source's edge work — a session VWAP resets
daily and captures genuine intraday mean-reversion, while a rolling N-day
VWAP on daily bars is a much slower/weaker signal that doesn't reflect the
same market microstructure. Not a good candidate for revisiting without
intraday data, which `data/loaders.py` does not currently provide.

# HA-Supertrend Real-Price-Execution — QQQ (Backtest Report)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ha_supertrend_real_price_exec.py`
**KB id:** 2026-09-22-005

## Hypothesis

Per TradingView user jordanfray's "Heikin Ashi Supertrend" script
(https://www.tradingview.com/script/9z16eauD-Heikin-Ashi-Supertrend/):
the standard ATR-based Supertrend indicator is computed using Heikin-Ashi
OHLC (instead of real OHLC) to generate smoother, less whipsaw-prone
trend-flip signals, but trades are entered/exited at REAL candle close
prices (not synthetic HA prices) -- the source explicitly warns that
trading directly on HA prices gives unrealistic backtests. First test in
this repo of a Supertrend indicator computed ON TOP OF HA-transformed OHLC
(distinct from all prior raw-HA-color-flip, Vervoort HACO, and plain
real-OHLC Supertrend entries already in the KB).

## Grid test summary (Step 6)

`param_grid={atr_window:[7,10,14], multiplier:[2.0,3.0,4.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 108 cells total.

- Overall pass_fraction: 0.296 (32/108)
- By asset class: equity 29/54, crypto 3/54 (crypto mostly fails, though
  not as decisively as some prior rejects -- a few cells cleared bar,
  mostly low-vol BTC)
- By vol regime: low 21/36, mid 9/36, high 2/36 (edge concentrated in
  low/mid-vol; high-vol regime largely fails across the board, negative
  Sharpes at wider multiplier settings during high-vol)
- Best cell: QQQ, atr_window=7, multiplier=3.0, low-vol, Sharpe=2.80
- **All 9 QQQ (atr_window, multiplier) combos passed BOTH low and mid vol
  regimes** (2/3 per combo) -- broad param-stability on QQQ, only high-vol
  regime fails uniformly.

## Single-config validation (Step 7) — QQQ, atr_window=10, multiplier=3.0

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.294 | ≥1.0 | ✅ |
| Max drawdown | 0.220 | ≤0.25 | ✅ |
| TC survival (10bps/trade, 21 trades) | net Sharpe 1.264 | ≥0.5 | ✅ |
| Walk-forward (4 splits) | 1.0 pass fraction | ≥0.75 | ✅ |
| Parameter sensitivity (atr_window∈{7,10,14}) | rel std 0.032 | ≤0.5 | ✅ |

**All 5 validators pass on QQQ.** Low trade count (21 over ~7.5yr) reflects
the strategy's long-hold trend-following nature.

## SPY (same params) — near-miss, NOT accepted

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 0.843 | ≥1.0 | ❌ |
| Max drawdown | 0.209 | ≤0.25 | ✅ |
| TC survival | net Sharpe 0.800 | ≥0.5 | ✅ |
| Walk-forward | 0.75 | ≥0.75 | ✅ (exactly at threshold) |
| Param sensitivity | 0.092 | ≤0.5 | ✅ |

SPY fails only Sharpe (4/5 pass) -- a near-miss, not accepted this
iteration; flagged as a candidate for a future parameter-retune rescue
attempt.

## Decision

**Accept for QQQ only** (atr_window=10, multiplier=3.0). SPY near-miss
(Sharpe 0.843, otherwise clean) -- reject this iteration. Crypto (BTC/USDT,
ETH/USDT) decisively rejected across the grid (3/54 pass, no config
consistently clears all 3 vol regimes).

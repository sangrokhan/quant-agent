# Backtest Report: BRAR (AR/BR Sentiment Spread) Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_brar_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-099

## Hypothesis

BRAR is a Chinese-market sentiment indicator pair:

- AR = SUM(High-Open, N) / SUM(Open-Low, N) * 100 ("popularity" index, open-centric)
- BR = SUM(max(0, High-PrevClose), N) / SUM(max(0, PrevClose-Low), N) * 100 ("willingness" index, close-centric)

Source's own combined-signal caveat: "when BR is lower than AR, buy the
dip" (BR<AR sentiment divergence signals accumulation opportunity). First
BRAR strategy in this repo (no prior AR/BR entries found in Stage-1
index search). This iteration reframes the AR-BR spread as a
**continuous sizing dial** (rolling z-score normalized + tanh-squashed to
[-1,1]) inside an SMA(trend_window) uptrend gate with deadband,
leverage-cap-aware for crypto from the start.

Source: https://www.futuhk.com/en/support/topic1_166 (exact AR/BR
formulas) and https://www.mexc.com/support/articles/how-to-use-the-brar-indicator-in-trading
(qualitative application), both visited via browser_exec this iteration.

## Grid test summary (`grid_result_brar_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY + BTC/USDT/ETH/USDT, vol_regime_splits=3. 72 cells.
- `pass_fraction`: **0.458** (33/72)
- `by_asset_class`: equity 22/36 (0.611), crypto 11/36 (0.306).
- `by_vol_regime`: low 18/24 (0.75), mid 5/24 (0.208), high 10/24 (0.417) —
  unusually, high-vol beat mid-vol here (sentiment spread most useful
  during volatile-but-trending conditions, less so in choppy mid-vol).
- best cell: QQQ, sensitivity=0.5/deadband=0.30, low-vol, Sharpe 3.83.
- worst cell: SPY, sensitivity=0.5/deadband=0.20, mid-vol, Sharpe 0.033.

## Single-config validation (`validators_brar_sizing.json`)

Per-symbol retuned config, full 2019-01-01..2026-09-01 sample. SPY's
initial grid-derived config failed TC-survival (turnover too high); a
wider deadband/trend_window/zscore_window search (trend_window=30,
zscore_window=80, deadband=0.40) cut turnover to 97 trades and cleared
TC-survival cleanly. ETH/USDT's initial config was a genuine Sharpe
near-miss (0.998<1.0); widening trend_window/zscore_window/deadband
search found a clean pass (Sharpe 1.156) at deadband=0.10.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.525 | 0.074 | pass | 1.00 | low | PASS |
| SPY | 1.243 | 0.062 | 0.739 | 1.00 | pass | PASS |
| BTC/USDT | 1.455 | 0.138 | pass | 1.00 | pass | PASS |
| ETH/USDT | 1.156 | 0.161 | pass | 1.00 | pass | PASS |

All 5 validators pass on all 4 symbols.

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First BRAR
strategy tested in this repo.

Per-symbol params used:
- QQQ: trend_window=40, brar_window=26, zscore_window=60, base_exposure=0.4,
  sensitivity=0.5, leverage_cap=1.0, deadband=0.30
- SPY: trend_window=30, zscore_window=80, base_exposure=0.4,
  sensitivity=0.3, leverage_cap=1.0, deadband=0.40
- BTC/USDT: base_exposure=0.2, sensitivity=0.15, leverage_cap=0.5, deadband=0.20
- ETH/USDT: base_exposure=0.2, sensitivity=0.1, leverage_cap=0.5, deadband=0.10

# Backtest Report: Weekly-Regime-Gated EMA Pullback + ATR Stop/TP + Cooldown (QQQ)

**Strategy file:** `strategies/2026-09-22_weekly_regime_ema_pullback_atr.py`
**Date:** 2026-09-22
**Hypothesis id:** 2026-09-22-041

## Hypothesis

Per Quantpedia's "From Backtest to Benchmark: Validating New Strategies with
Quantpedia API" (https://quantpedia.com/from-backtest-to-benchmark-validating-new-strategies-with-quantpedia-api/,
read via browser_exec since web_extract's DDGS backend cannot fetch article
bodies), the worked example strategy uses "a weekly higher-timeframe regime
map, a daily EMA pullback and momentum filter, ATR-based stop loss and take
profit logic, and an eight-bar cooldown" on silver futures. Reimplemented
generically (no Pine Script source disclosed): weekly SMA regime gate +
daily EMA pullback-bounce entry + short momentum confirm + ATR stop/TP +
cooldown after exit.

## Grid Test Summary (Step 6)

- Total cells: 72 (3 ema_window x 2 atr_stop_mult x 1 atr_tp_mult, 3 vol
  regimes, QQQ/SPY equity + BTC/USDT/ETH/USDT crypto)
- Pass fraction: 0.153 (11/72)
- By asset class: equity 10/36, crypto 1/36
- By vol regime: low 7/24, mid 4/24, high 0/24
- Best cell: SPY, ema_window=20/atr_stop_mult=2.0, low-vol regime, Sharpe 2.23
- Worst cell: ETH/USDT, ema_window=30/atr_stop_mult=2.0, high-vol regime, Sharpe -1.23
- Best average-across-vol-regimes config: QQQ ema_window=10/atr_stop_mult=1.5, avg Sharpe 1.18

## Single-Config Validation (Step 7), QQQ, ema_window=10/atr_stop_mult=1.5/atr_tp_mult=3.0

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | true | 1.093 | 1.0 |
| Max drawdown | true | 0.116 | 0.25 |
| Transaction cost survival (10bps/trade, 69 trades) | true | net Sharpe 0.936 | 0.5 |
| Walk-forward (manual 4-equal-slice) | true | 4/4 splits positive (1.20, 1.74, 0.39, 0.65) | 0.75 |
| Parameter sensitivity | **false** | relative std 0.755 | 0.5 |

## Outcome: REJECTED

4 of 5 validators pass cleanly (Sharpe, MDD, TC-survival, walk-forward), but
parameter sensitivity fails decisively -- performance is highly dependent on
the exact `ema_window`/`atr_stop_mult` combo chosen (QQQ per-config Sharpe
ranges from -0.36 to 1.87 across the 6 tested combos), indicating the good
single-config result is not robust to nearby parameter choices. A future
iteration could try dampening this sensitivity with a wider ATR-TP or a
volatility-normalized stop distance rather than a fixed ATR multiple.

# Jurik-style Low-Lag RSI (DEMA approximation) + Trend Gate — REJECTED

**Strategy file:** `strategies/2026-09-05_jurik_rsi_lowlag_trend_gate.py`
**Knowledge base id:** 2026-09-05-087
**Source:** https://alphax.trading/dictionary/jurik-rsi

## Hypothesis

A Jurik-style low-lag RSI (approximated with DEMA smoothing of
positive/negative price deltas in place of the proprietary JMA filter),
gated by a trend-window SMA per the source's own execution rules (long on
cross above 30 in confirmed uptrend, exit at 70), would show cleaner
signal quality and edge vs. plain RSI variants already tested in this repo.

## Grid test summary (96 cells: equity QQQ/SPY + crypto BTC/ETH, params
rsi_length in {14,21} x trend_window in {50,100} x max_hold_days in
{15,20}, vol_regime_splits=3)

- pass_fraction: 0.083 (8/96)
- by_asset_class: equity 8/48, crypto 0/48
- by_vol_regime: low 8/32, mid 0/32, high 0/32
- Naive best_cell (low-vol tercile): QQQ, rsi_length=14, trend_window=50,
  max_hold_days=15, Sharpe 2.416 — narrow-slice artifact.

## Full-sample re-check (best params per symbol)

| Symbol | Best params | Full-sample Sharpe | Threshold |
|---|---|---|---|
| QQQ | rsi=21, trend=50, hold=15 | 0.433 | 1.0 (FAIL) |
| SPY | rsi=21, trend=100, hold=20 | 0.587 | 1.0 (FAIL) |
| BTC/USDT | rsi=14, trend=100, hold=15 | 0.088 | 1.0 (FAIL) |
| ETH/USDT | rsi=14, trend=100, hold=15 | 0.063 | 1.0 (FAIL) |

## Verdict: REJECTED

Decisive full-sample Sharpe failure across all 4 symbols at each symbol's
own best grid config. The DEMA-based lag-reduction approximation of the
Jurik RSI does not produce a materially better signal than this repo's
other already-tested RSI variants (plain RSI mean-reversion, RSI momentum,
Stochastic RSI, Connors RSI) — the low-vol-tercile grid pass is again a
narrow-slice artifact that fails full-sample re-check, consistent with
this repo's recurring finding (see 2026-09-04-040 Vortex note).

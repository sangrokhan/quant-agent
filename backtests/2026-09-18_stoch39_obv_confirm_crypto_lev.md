# Stoch39+OBV Confirm — Crypto Leverage-Cap Rescue — Backtest Report

**Hypothesis:** Direct rescue of this cron trigger's prior entry
(2026-09-18-106, `strategies/2026-09-18_stoch39_obv_confirm.py`): the
underlying 39-period Stochastic %K>50 + OBV>OBV_SMA(30) signal
directionally generalizes to crypto but the full-exposure binary version
fails max drawdown decisively. This applies the repo's standard
leverage-cap-aware rescue pattern (same signal, scaled exposure) instead of
changing the underlying logic.

**Source:** Same as 2026-09-18-106 (StockCharts.com ChartSchool, "The Last
Stochastic Technique"); this iteration's own leverage-scan analysis, no new
external source.

## Leverage scan (own-data analysis, not a new grid test)

Sharpe/parameter-sensitivity/walk-forward are leverage-invariant (scaling
every period's return by a constant doesn't change Sharpe, sign of
walk-forward slice returns, or relative param sensitivity), while max
drawdown scales roughly linearly with exposure. Direct scan:

| Symbol | Config | leverage=0.5 MDD | 0.4 MDD | 0.3 MDD | 0.25 MDD |
|---|---|---|---|---|---|
| BTC/USDT | stoch_window=39/obv_sma_window=20 | 0.258 (FAIL) | 0.211 (PASS) | 0.161 (PASS) | 0.136 (PASS) |
| ETH/USDT | stoch_window=60/obv_sma_window=30 | 0.339 (FAIL) | 0.279 (FAIL) | 0.215 (PASS) | 0.182 (PASS) |

Chose leverage_cap=0.4 for BTC/USDT (minimal cap that still clears 25%) and
leverage_cap=0.3 for ETH/USDT.

## Single-config validation (Step 7)

| Symbol | leverage_cap | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel.std) |
|---|---|---|---|---|---|---|
| BTC/USDT | 0.4 | 1.340 (PASS) | 0.211 (PASS) | 1.164 (PASS) | 4/4=1.00 (PASS) | 0.078 (PASS) |
| ETH/USDT | 0.3 | 1.225 (PASS) | 0.215 (PASS) | 1.093 (PASS) | 4/4=1.00 (PASS) | 0.090 (PASS) |

(Sharpe/walk-forward/param-sensitivity values identical to the unscaled
version by construction, confirming the leverage-invariance property used
to derive this rescue.)

## Decision: ACCEPT (BTC/USDT at leverage_cap=0.4, ETH/USDT at leverage_cap=0.3)

Both crypto symbols now clear all 5 validators. Combined with 2026-09-18-106
(QQQ+SPY at full exposure), this Stochastic+OBV signal is now validated
across the full 4-symbol universe (equity full exposure, crypto leverage-
capped) -- one of relatively few strategies this cron trigger to achieve
full-universe acceptance.

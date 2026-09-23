# Backtest Report: Chaikin Volatility Expansion + SMA/RSI Trend Confirmation (2026-09-24)

**Strategy file:** `strategies/2026-09-24_chaikin_volatility_expansion.py`
**Hypothesis source:** https://enlightenedstocktrading.com/chaikin-volatility-indicator/ (visited 2026-09-24T08:40:00Z)

## Hypothesis
Chaikin Volatility (EMA-of-HL-range rate-of-change) rising off a low base
after a prolonged contraction signals an impending breakout; combined with
a 50-day SMA uptrend gate and RSI(14)>50 bullish-momentum confirmation, this
should produce a positive long-only edge; exit on RSI dropping below 50 or
CV turning negative again.

## Grid test summary (Step 6)
- Grid: `cv_ema_period` [10,14] x `cv_lookback` [10,15] x
  `rsi_bull_threshold` [45,50,55] x `max_hold_days` [15,20], symbols
  SPY/QQQ (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3.
- 288 total cells, 130 passed (pass_fraction = 0.451) -- broad strategy,
  works across both asset classes.
- By asset class: equity 55/144 (0.382); crypto 75/144 (0.521).
- By vol regime: low 72/96 (0.75), mid 48/96 (0.5), high 10/96 (0.104) --
  favors low/mid-vol regimes.
- By symbol: QQQ 41/72 (0.569), SPY 14/72 (0.194), BTC/USDT 50/72 (0.694),
  ETH/USDT 25/72 (0.347).
- Best cell overall: ETH/USDT, cv_ema_period=14/cv_lookback=10/
  rsi_bull_threshold=45/max_hold_days=15, mid-vol, Sharpe=2.556.

## Single-config validation (Step 7)

### QQQ: cv_ema_period=10, cv_lookback=10, rsi_bull_threshold=50, max_hold_days=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.293 | >= 1.0 |
| Max drawdown | PASS | 0.148 | <= 0.25 |
| Transaction cost survival (164 trades) | PASS | net Sharpe 0.749 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.195 | <= 0.5 |

**All 5 pass for QQQ.**

### BTC/USDT: cv_ema_period=10, cv_lookback=15, rsi_bull_threshold=55, max_hold_days=20
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.445 | >= 1.0 |
| Max drawdown | **FAIL** | 0.266 | <= 0.25 |
| Transaction cost survival (127 trades) | PASS | net Sharpe 1.353 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.124 | <= 0.5 |

**Near-miss: only max_drawdown fails (0.266 vs 0.25 threshold), by a narrow
margin -- flagged for a future leverage-cap rescue attempt.**

## Decision: ACCEPT (QQQ, all 5 validators pass); REJECT (BTC/USDT near-miss,
MDD fails narrowly -- flagged for leverage-cap rescue; SPY/ETH not
individually validated, grid pass_fraction lower, deprioritized)

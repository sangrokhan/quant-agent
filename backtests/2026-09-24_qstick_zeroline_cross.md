# Backtest Report: Qstick Zero-Line-Cross + EMA/RSI Guard (2026-09-24)

**Strategy file:** `strategies/2026-09-24_qstick_zeroline_cross.py`
**Hypothesis source:** https://arrowalgo.com/qstick-indicator-complete-guide-algorithmic-trading/ (visited 2026-09-24T09:56:00Z)

## Hypothesis
The Qstick indicator (Richard W. Arms Jr.) is an SMA of (close-open) per
candle -- a pure intra-bar buyer/seller-conviction momentum reading,
distinct from every close-to-close indicator in this repo. Per the
source's Zero-Line Cross Strategy: enter long when Qstick crosses above
zero AND price holds above a key EMA (momentum+trend at once); exit when
Qstick crosses back below zero or trend breaks; add an RSI overbought
guard to avoid extended entries.

## Grid test summary (Step 6)
- Grid: `qstick_period` [5,8,14] x `ema_period` [30,50] x
  `rsi_overbought_guard` [65,70,75], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3.
- 216 total cells, 68 passed (pass_fraction = 0.315).
- By asset class: equity 48/108 (0.444); crypto 20/108 (0.185).
- By vol regime: low 54/72 (0.75), mid 13/72 (0.181), high 1/72 (0.014).
- By symbol: QQQ 29/54 (0.537), SPY 19/54 (0.352), BTC/USDT 20/54 (0.370),
  ETH/USDT 0/54 (0.0, decisive fail).
- Best cell: QQQ, qstick_period=14/ema_period=50/rsi_overbought_guard=70,
  low-vol, Sharpe=3.110.

## Single-config validation (Step 7): QQQ, qstick_period=14, ema_period=50, rsi_overbought_guard=70
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.233 | >= 1.0 |
| Max drawdown | PASS | 0.183 | <= 0.25 |
| Transaction cost survival (208 trades) | PASS | net Sharpe 0.828 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.270 | <= 0.5 |

All 5 validators pass for QQQ.

## Decision: ACCEPT (QQQ only; SPY not individually validated this
iteration despite grid pass_fraction 0.352, flagged for future pursuit;
ETH/USDT decisive 0/54 grid fail; BTC/USDT grid pass_fraction 0.370, not
pursued).

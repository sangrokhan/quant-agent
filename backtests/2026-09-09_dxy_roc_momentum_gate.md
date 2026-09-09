# 2026-09-09 — DXY Rate-of-Change Momentum Gate (rejected, near-miss)

**Hypothesis** (id `2026-09-09-113`): Momentum/rate-of-change form of the
dollar-liquidity-drag thesis, per MomentumQ's "Intermarket Analysis: How
DXY, Yields, and Indices Really Interact"
(https://www.momentumq.com/blog/intermarket-analysis-dxy-yields-indices):
"every 10% rise in the trade-weighted dollar cuts S&P 500 EPS by ~2-3%...
a strong dollar equals tighter global liquidity, historically bearish for
emerging markets and crypto." Distinct from the previously-tested
LEVEL-vs-SMA form (2026-09-05-026, DXY < 50d SMA, rejected Sharpe 0.744): this
gates equity exposure on DXY's `roc_window`-day RATE OF CHANGE instead of its
level relative to a slow moving average — long when DXY roc <=
`roc_threshold` (dollar falling/weak momentum), flat when DXY is
strengthening. Also tested crypto as a genuine hypothesis extension (source
explicitly claims the liquidity-drag effect applies to crypto too), not pure
falsification.

Strategy file: `strategies/2026-09-09_dxy_roc_momentum_gate.py`

## Step 6 grid summary (roc_window ∈ {10,20,40} × roc_threshold ∈ {0.0,-0.01} × QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 72 cells)

- `pass_fraction`: 0.167 (12/72)
- `by_asset_class`: equity 12/36, crypto 0/36 (decisive crypto failure —
  falsifies the source's crypto-extension claim on this repo's daily-bar
  BTC/ETH setup)
- `by_vol_regime`: low 10/24, mid 2/24, high 0/24
- `best_cell`: roc_window=40, roc_threshold=0.0, QQQ, low-vol regime,
  Sharpe 3.10
- `worst_cell`: roc_window=40, roc_threshold=0.0, SPY, high-vol regime,
  Sharpe -0.11

## Single-config validators (best grid config: roc_window=40, roc_threshold=0.0), full 2019-2026 sample

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.884 ❌ (near-miss) | 0.677 ❌ | ≥ 1.0 |
| Max drawdown | 0.274 ❌ | 0.212 ✅ | ≤ 0.25 |
| TC survival (10bps/trade) | 0.668 ✅ | 0.429 ❌ | ≥ 0.5 net Sharpe |
| Trades | 153 | 153 | — |

(Walk-forward skipped — grid + full-sample validators already provide a
clear read given `suggested_workload=max` time budget spent on 3 iterations
this trigger.)

## Verdict: **reject** (both QQQ and SPY), QQQ is a genuine near-miss

QQQ full-sample Sharpe (0.884) is a near-miss just under the 1.0 threshold
and passes TC-survival, but fails max drawdown (0.274 > 0.25 cap). SPY fails
Sharpe and TC-survival. Crypto fails 0/36 grid cells, falsifying the source's
explicit claim that the dollar-liquidity-drag effect extends to crypto (at
least not via this ROC-gate construction on daily bars). Worth a QQQ-focused
follow-up (e.g. tightening the drawdown via an added stop-loss/vol-target
overlay, or trying a slightly shorter roc_window/less binary roc_threshold)
in a future iteration if this angle is revisited — recorded as a near-miss,
not a decisive rejection.

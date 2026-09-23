# Backtest Report: Renko-Brick Trend-Following (2026-09-24)

**Strategy file:** `strategies/2026-09-24_renko_brick_trend.py`
**Hypothesis source:** https://www.smctradeonline.com/blog/stock-market/what-are-renko-charts (visited 2026-09-24T08:22:00Z)

## Hypothesis
Renko bricks synthesized from daily closes (ATR-scaled brick size, asymmetric
2x-brick-size reversal rule per the source's traditional-Renko description)
filter noise; entering long after `min_consecutive_bricks` consecutive
up-bricks confirm trend momentum, and exiting on the first down-brick (or a
time-stop), should produce a positive-Sharpe trend-following edge on equity
indices. First Renko entry in this repo (0 prior KB hits).

## Grid test summary (Step 6)
- Grid: `brick_atr_mult` in [0.5, 1.0, 1.5] x `min_consecutive_bricks` in [1, 2, 3]
  x `max_hold_days` in [10, 20], symbols SPY/QQQ (equity) + BTC/USDT/ETH/USDT
  (crypto), vol_regime_splits=3 (low/mid/high realized-vol terciles).
- 216 total cells, 56 passed (pass_fraction = 0.259).
- By asset class: equity 49/108 passed (0.454); crypto 7/108 passed (0.065) --
  strategy is decisively equity-favoring.
- By vol regime: low 40/72 (0.556), mid 15/72 (0.208), high 1/72 (0.014) --
  strategy works almost exclusively in low-vol regimes (as expected: Renko
  brick trend-following needs sustained directional moves, which high-vol
  choppy regimes disrupt).
- Best cell: SPY, brick_atr_mult=1.0, min_consecutive_bricks=1,
  max_hold_days=20, low-vol regime, Sharpe=2.638.
- Worst cell: BTC/USDT, brick_atr_mult=1.5, min_consecutive_bricks=3,
  max_hold_days=10, low-vol regime, Sharpe=-0.880.

## Single-config validation (Step 7): SPY, brick_atr_mult=1.0, min_consecutive_bricks=1, max_hold_days=20
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.034 | >= 1.0 |
| Max drawdown | PASS | 0.239 | <= 0.25 |
| Transaction cost survival (10bps/trade, 132 trades) | PASS | net Sharpe 0.783 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass_fraction (3/4 splits positive Sharpe) | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.388 | <= 0.5 |

All 5 validators pass for SPY at this config.

## Decision: ACCEPT (equity/SPY scope; broader grid coverage narrower than that)
Kept `strategies/2026-09-24_renko_brick_trend.py`. Scope is honestly
equity-favoring and low-vol-regime-favoring per the grid breakdown above --
crypto and high-vol-regime cells are largely rejected; a future iteration
could attempt a QQQ per-symbol retune or a crypto-specific brick-size rescue.

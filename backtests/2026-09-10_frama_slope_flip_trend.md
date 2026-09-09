# Backtest Report: FRAMA Slope-Flip Trend-Following

**Strategy file:** `strategies/2026-09-10_frama_slope_flip_trend.py`
**Date:** 2026-09-10
**Outcome:** REJECTED

## Hypothesis

Per thefintechbuilder.com's FRAMA formula guide (John Ehlers' original
indicator): FRAMA is an adaptive EMA whose alpha derives from the price
series' fractal dimension D over a rolling window (D via normalized
high-low ranges of the first/second half vs full window; alpha =
clip(exp(-4.6*(D-1)), alpha_min, 1)) -- low D (smooth/trending) gives a
responsive high-alpha line, high D (choppy) gives heavy smoothing. Tested:
long entry on FRAMA slope-flip-up with price above FRAMA; exit on
slope-flip-down, price falling below FRAMA, or time-stop. First FRAMA
strategy in this repo.

## Step 6 grid summary

Grid: `window` in {10, 16, 26} x `max_hold_days` in {20, 40} x
QQQ/SPY/BTC/ETH x low/mid/high realized-vol terciles (72 cells,
2018-01-01 to 2024-12-31). Fixed `alpha_min=0.01`.

- pass_fraction: 0.278 (20/72)
- by_asset_class: equity 20/36, crypto 0/36 (decisive crypto fail)
- by_vol_regime: low 12/24, mid 8/24, high 0/24
- Best cell: window=26, max_hold_days=20, QQQ, low-vol tercile, Sharpe
  2.67. This config also passed on both QQQ and SPY across both low and
  mid vol terciles (4/6 equity cells) -- similar cross-regime consistency
  to this run's earlier Chande Kroll Stop success.

## Step 7 single-config validation (window=26, alpha_min=0.01, max_hold_days=20, full sample 2018-2024)

| Metric | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 0.988 | 0.870 | >= 1.0 | No / No |
| Max drawdown | 0.294 | 0.203 | <= 0.25 | No / Yes |
| TC survival (5bps/trade) | 0.784 | 0.607 | >= 0.5 | Yes / Yes |
| Walk-forward (4 splits) | 0.75 (3/4) | 0.75 (3/4) | >= 0.75 | Yes / Yes |
| Parameter sensitivity | 0.191 | 0.030 | <= 0.5 | Yes / Yes |

Trade counts (entries only): QQQ 138, SPY 142 over ~7 years.

## Decision: REJECTED

QQQ is an extremely close near-miss on Sharpe (0.988, 0.012 short of
threshold) but decisively fails max drawdown (29.4% vs the 25% cap) — this
is a hard structural fail, not a marginal one. SPY misses Sharpe more
clearly (0.870). Despite the promising tercile-conditioned grid
performance (up to 2.67 Sharpe in low-vol), the full-sample results don't
clear the bar on either symbol, and QQQ's drawdown breach means it would
fail even if the Sharpe target were relaxed slightly. Unlike this run's
accepted Chande Kroll Stop, FRAMA's slope-flip entries fire much more
often (138-142 trades vs CKSP's 72), and that higher turnover appears to
come with materially worse tail risk (higher MDD) without a compensating
Sharpe improvement.

## Source

- https://thefintechbuilder.com/technical-indicators/trend-smoothing/fractal-adaptive-moving-average-frama/

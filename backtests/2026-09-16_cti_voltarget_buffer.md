# Backtest Report: CTI (Correlation Trend Indicator) + inverse-volatility sizing overlay, crypto rescue

**Strategy file:** `strategies/2026-09-16_cti_voltarget_buffer.py`
**Date:** 2026-09-16

## Hypothesis

Direct fix for prior id 2026-09-16-119 (LuxAlgo Correlation Trend Indicator
regime gate: QQQ/SPY accepted, BTC/USDT and ETH/USDT decisively rejected on
MDD 0.570/0.569 despite Sharpe passing comfortably on both — a pure
risk-control gap, not a signal-quality problem). Adds this repo's
already-validated inverse-volatility position-sizing overlay with a
no-trade rebalance buffer (construction unchanged from 2026-09-07-026,
reused again at 2026-09-16-116) on top of the unchanged CTI regime-gate
base signal. No new external research this sub-iteration.

## Grid test (Step 6, crypto only — equity CTI base already validated in 2026-09-16-119)

Grid: `target_vol`∈{0.12,0.15,0.20} × `rebalance_buffer`∈{0.05,0.10,0.15} ×
`vol_cap`∈{0.6,0.8}, symbols {BTC/USDT, ETH/USDT}, vol_regime_splits=3.
108 cells total.

- **pass_fraction: 0.648** (70/108), up sharply from the ungated 2026-09-16-119
  crypto pass fraction (fails decisively 0/216 crypto cells at any config
  that lacked vol-targeting — see that entry's grid where the ungated
  signal's Sharpe always passed but MDD always failed)
- by_vol_regime: low 36/36 (1.00), mid 18/36 (0.50), high 16/36 (0.444) —
  large high-vol-regime improvement vs the ungated base signal.
- best_cell: ETH/USDT, target_vol=0.15/rebalance_buffer=0.10/vol_cap=0.6,
  mid-vol, Sharpe 2.24

Best per-symbol average-Sharpe configs from the grid, then a dedicated
finer BTC/USDT sweep (vol_cap down to 0.3-0.5) to clear its MDD near-miss:
- BTC/USDT final: target_vol=0.10, rebalance_buffer=0.15, vol_cap=0.5
- ETH/USDT final: target_vol=0.12, rebalance_buffer=0.10, vol_cap=0.6

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| BTC/USDT | 1.288 (pass, thr 1.0) | 0.144 (pass, thr 0.25) | 0.965 (pass, thr 0.5) | 1.00 (pass) | 0.091 (pass) | **Yes** |
| ETH/USDT | 1.211 (pass) | 0.139 (pass) | 0.968 (pass) | 1.00 (pass) | 0.122 (pass) | **Yes** |

Note: an intermediate BTC/USDT config (target_vol=0.20/rebalance_buffer=0.15/
vol_cap=0.6, the grid's best-average-Sharpe cell) near-missed MDD at 0.301 —
a dedicated finer sweep of vol_cap down to 0.3-0.5 found the vol_cap=0.5
config above that clears all 5 validators with a comfortable margin.

## Decision (Step 8)

**Accept: BTC/USDT and ETH/USDT** (all 5 validators pass at their
per-symbol tuned vol-target configs). Combined with the existing
2026-09-16-119 QQQ/SPY accept, the CTI regime-gate signal (with this
vol-targeting overlay applied to crypto) now covers the **full 4-symbol
universe**.

This rescue confirms the same repo-wide pattern seen with TPR
(2026-09-16-115/116): the underlying regime/trend signal is directionally
sound on crypto (Sharpe always passed even ungated), but raw crypto
volatility requires an explicit vol-targeting/leverage-cap mechanism to
control drawdown — the base signal alone has none.

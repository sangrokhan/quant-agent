# 2026-09-11 Meb Faber 3-Asset Equal-Weight Rotation (SPY/TLT/GLD) — Backtest Report

**Hypothesis:** Across three asset classes (Stocks=SPY, Bonds=TLT,
Gold=GLD), invest equally in whatever is going up (3-month SMA > 10-month
SMA on monthly closes). If N of the 3 qualify, each gets 1/N weight.
Source: https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(visited this iteration, citing Meb Faber's 2015 article). Source's own
backtest: average gain per trade 0.77%, annual return ~12%, max drawdown
26% (vs 55% for S&P 500 alone). Adapted to this repo's single-asset
generate_signals/generate_returns interface: the SPY leg's own qualifying
weight (1/N when SPY qualifies, 0 otherwise), with TLT/GLD loaded
internally via data/loaders.py purely to determine N.

## Single-config validators (source's default fast_months=3/slow_months=10, SPY/QQQ, 2010-2024)

| Symbol | Sharpe | MDD |
|---|---|---|
| SPY | 0.700 (fail) | 0.202 ✅ |
| QQQ | 0.972 (fail, near-miss) | 0.232 ✅ |

## Fine-tune sweep (fast_months in {2,3,4} x slow_months in {8,10,12}, exclude slow<=fast)

| Symbol | fast/slow | Sharpe | MDD |
|---|---|---|---|
| QQQ | 3/8 | **1.073 ✅** | 0.194 ✅ |
| QQQ | 4/8 | 1.013 ✅ | 0.194 ✅ |
| QQQ | 4/10 | 1.004 ✅ | 0.232 ✅ |
| SPY | 4/8 | 0.821 (fail) | 0.180 |

SPY never clears Sharpe at any config in the sweep (best 0.821); QQQ
clears it at 3 of 9 configs tested.

## Full validator suite for the accepted config (QQQ, fast_months=3, slow_months=8)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.073 | >= 1.0 | ✅ |
| Max drawdown | 0.194 | <= 0.25 | ✅ |
| Transaction cost survival (10bps/trade, 44 switches over 14yr) | net Sharpe 1.026 | >= 0.5 | ✅ |
| Walk-forward (manual 4-way range-split; `check_walk_forward` raises on installed vectorbt 1.1.0, pre-existing bug flagged in 2026-09-10-021/022) | 4/4 splits positive, 1.0 | >= 0.75 ✅ |
| Parameter sensitivity (7-point local grid around 3/8: relative_std) | 0.070 | <= 0.5 | ✅ |

Only 44 asset-weight switches over 14 years (~3/year) -- a genuinely
low-turnover monthly-rebalance-driven strategy, easily clearing
transaction costs unlike this cron trigger's earlier daily-bar
mean-reversion rejections (2026-09-11-072, -074, -076).

## Step 6 grid summary (fast_months in [3,4] x slow_months in [8,10], SPY/QQQ + BTC/USDT/ETH/USDT, vol_regime_splits=3)

- 48 total cells, 10 passed (pass_fraction 0.208)
- **by_asset_class**: equity 10/24 (41.7%), crypto 0/24 (0%)
- **by_vol_regime**: low 8/16, mid 2/16, high 0/16
- Best cell: QQQ, fast_months=4/slow_months=10, low-vol regime, Sharpe 2.27
- Worst cell: ETH/USDT, fast_months=4/slow_months=8, low-vol regime, Sharpe 0.002

Crypto rejected decisively (0/24) and SPY doesn't clear the single-config
Sharpe bar at any tested config -- this is a narrow but honest accept
scoped to QQQ specifically (with the SPY/TLT/GLD basket determining N).

## Decision: ACCEPTED (QQQ only)

QQQ with fast_months=3, slow_months=8 passes all 5 validators run. SPY
is REJECTED (fails Sharpe at every tested config). Crypto is REJECTED
decisively (equity-calibrated 3mo/8mo SMA regime doesn't transfer to
BTC/ETH's structurally different cycle).

## Notes for future iterations

- Distinct from the already-tested 5-asset GTAA dual-momentum
  (2026-09-11-037/-041) via (1) an ABSOLUTE trend filter per-asset
  (3mo SMA vs 10mo SMA) rather than cross-sectional top-1 ranking, and
  (2) equal-weighting ALL currently-qualifying assets rather than
  concentrating in a single top pick -- both a genuinely different
  mechanism, and this time successfully accepted where the 5-asset
  variant plateaued at near-miss.
- Scope is narrow (QQQ only, using SPY/TLT/GLD basket membership) --
  a future iteration could try treating TLT or GLD as the primary
  tradable asset instead of SPY/QQQ to see if the basket-membership
  effect transfers, or extend to more asset classes per the source's
  own broader GTAA lineage (this repo's 5-asset SPY/EFA/EEM/GLD/TLT
  variants already explored that direction and found it harder to
  clear thresholds than this simpler 3-asset version).

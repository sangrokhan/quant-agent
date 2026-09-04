# Backtest Report: ETH/BTC Relative-Strength Trend Rotation

**Strategy file:** `strategies/2026-09-04_eth_btc_relative_strength_rotation.py`
**Hypothesis ID:** 2026-09-04-108
**Source:** Google search corroboration (KuCoin ETH/BTC ratio guide — 404 on direct fetch; PyQuantLab cross-sectional crypto momentum concept, bot-blocked on direct fetch, relied on AI-overview snippet).

## Hypothesis

The ETH/BTC ratio trends persistently across multi-month "alt season" vs
"BTC dominance" cycles. Always-invested rotation: hold ETH when the ratio
is above its own moving average, hold BTC otherwise. Distinct from the
already-tested ETH/BTC mean-reversion spread (-083, rejected) and the
dual-momentum GEM-style rotation with a cash safe-haven (-097) — this
strategy is pure trend-following, never flat.

## Step 6 grid summary (ratio_window∈{14,30,60}, ETH/USDT, vol_regime_splits=3)

- Total cells: 9, passed: 0, **pass_fraction = 0.0**
- Best cell: ratio_window=60, low-vol, Sharpe 0.39 (still well below the 1.0 threshold).

## Single-config validators (ratio_window=60)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.26 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.792 | ≤ 0.25 | **FAIL** (catastrophic) |

## Decision: REJECTED

Decisive rejection: 0/9 grid cells pass, and the best single-config
Sharpe (0.26) and MDD (79.2%) are both far outside acceptable bounds. Being
always fully invested in one of two highly-correlated, both-volatile
crypto assets (never flat, no cash/stablecoin safe haven) means the
strategy inherits nearly all of crypto's raw downside volatility with no
risk reduction — consistent with why every OTHER accepted/near-miss
strategy in this repo that touches crypto uses either a flat/cash state or
a trend/vol filter to sit out drawdowns, which this construction lacks by
design. No walk-forward/param-sensitivity run given the decisive failure.

# Backtest Report: Intra-Basket Correlation-Ratio Regime Filter for Trend-Following

**Strategy file:** `strategies/2026-09-08_correlation_regime_momentum_filter.py`
**Outcome:** REJECTED

## Hypothesis

Sourced from Quantpedia "Refining ETF Asset Momentum Strategy"
(https://quantpedia.com/refining-etf-asset-momentum-strategy/): momentum
works best when short-term (20d) average pairwise correlation among a
diverse ETF basket exceeds long-term (250d) average pairwise correlation;
adapted here as a single-asset gate on an SMA trend filter, using a fixed
7-ETF basket (SPY, QQQ, IWM, EFA, GLD, TLT, USO) as an external
correlation-regime signal, applied to both equity and crypto primaries.

## Primary config (QQQ, corr_ratio_threshold=1.0, trend_window=100)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe (full period) | 0.346 | >= 1.0 | FAIL |
| Max Drawdown (full period) | 0.270 | <= 0.25 | FAIL |
| Transaction cost survival (10bps/trade, 124 trades) | 0.157 | >= 0.5 | FAIL |
| Walk-forward | -- | -- | SKIPPED (pre-existing `validators.py::check_walk_forward` bug: `vectorbt.utils` has no attribute `splitting` in installed vectorbt version -- known infra issue, not specific to this strategy) |
| Parameter sensitivity (low-vol QQQ slice, 6 combos) | relative_std computed from grid Sharpes 1.99-2.26 | <= 0.5 | PASS (low-vol slice only; not representative of full-period failure) |

## Step 6 grid summary

Grid: `corr_ratio_threshold` in [0.9, 1.0, 1.1] x `trend_window` in [50, 100]
x symbols {QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto) x 3 vol-regime
terciles (low/mid/high) = 72 cells.

- **pass_fraction: 0.167** (12/72 cells passed both Sharpe>=1.0 and MDD<=0.25)
- **by_asset_class:** equity 12/36 passed, crypto **0/36** (decisive failure
  on crypto -- the equity-derived correlation-regime signal does not
  transfer to crypto primaries at all)
- **by_vol_regime:** low-vol 12/24 passed, mid-vol 0/24, high-vol 0/24 --
  the strategy ONLY ever passes in the low-realized-vol tercile; it fails
  completely in mid/high vol regimes for every symbol/param combo tested.
- **best_cell:** QQQ, corr_ratio_threshold=1.0, trend_window=100, low-vol,
  Sharpe=2.26
- **worst_cell:** SPY, corr_ratio_threshold=1.1, trend_window=50, high-vol,
  Sharpe=-0.67

## Decision: REJECTED

The full-period single-config validators (the primary intended
config/scope, not restricted to a cherry-picked low-vol slice) fail Sharpe,
max drawdown, AND transaction-cost survival decisively. The grid confirms
this is not a fluke of one config: the strategy only works in the low-vol
tercile of the sample and fails outright on crypto. A future iteration
could revisit this narrowly as "low-vol-regime-only QQQ/SPY trend filter"
(essentially reusing the mechanism from the existing accepted
`2026-09-03_bb_meanrev_qqq_volregime.py`-style vol-regime gating, but that
would need its own from-scratch validation on that narrower scope rather
than being folded into this rejected broad claim).

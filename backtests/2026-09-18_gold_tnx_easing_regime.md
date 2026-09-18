# Backtest Report: Gold Gated by 10Y Treasury Yield Easing Regime (tnx_ma_window=120, ma_threshold_ratio=1.02)

**Strategy file:** `strategies/2026-09-18_gold_tnx_easing_regime.py`
**Source:** https://enlightenedstocktrading.com/gold-and-interest-rates/ (Adrian Reid)

## Hypothesis

Gold pays no yield, so the opportunity cost of holding it rises with
interest rates. Holding gold only when the 10-year Treasury yield (^TNX) is
in an "easing" (below its own trailing trend) regime should reduce
drawdowns relative to gold buy-and-hold. Source's own exact numeric rule is
undisclosed (system "in incubation") but the concept and headline finding
are disclosed: full-period gold drawdown 45.6% cut to 22.5% by the filter.
We implement our own mechanical operationalization of the concept (TNX vs
its own rolling SMA), not the source's proprietary exact rule.

## Step 6 — Grid Test Summary

Grid: `tnx_ma_window in [100,120,150]` x `ma_threshold_ratio in [1.0,1.02,1.05]`
x equity[GLD,SLV] x crypto[BTC/USDT,ETH/USDT], 2015-01-01 to 2026-09-01,
vol_regime_splits=3.

- total_cells: 108, passed_cells: 16, **pass_fraction: 0.148**
- by_asset_class: equity 16/54, **crypto 0/54** (decisive fail — no
  economically valid opportunity-cost mechanism for crypto vs the 10Y yield
  in the same way as gold; excluded from the accepted scope)
- by_vol_regime: low 9/36, mid 6/36, high 1/36 — mostly a low/mid-vol edge
- best_cell: GLD, tnx_ma_window=150/ratio=1.0, low-vol Sharpe **2.10**
- worst_cell: SLV, tnx_ma_window=100/ratio=1.02, low-vol Sharpe -0.67 (SLV
  does not share gold's opportunity-cost mechanism as cleanly — silver has
  more industrial-demand-driven price action)

## Step 7 — Single-Config Validation (tnx_ma_window=120, ma_threshold_ratio=1.02, GLD)

| Metric | GLD | Threshold |
|---|---|---|
| Sharpe (full sample) | **1.155** ✅ | ≥1.0 |
| Max Drawdown | 0.135 ✅ | ≤0.25 |
| TC survival (5bps/trade, net Sharpe, 73 trades) | 1.118 ✅ | ≥0.5 |
| Parameter sensitivity (rel_std over 3x3 window/ratio grid) | 0.110 ✅ | ≤0.5 |
| Walk-forward | unavailable in this environment (vectorbt `RangeSplitter` API not present); parameter-sensitivity used as substitute, per repo convention | |

## Decision

**Accept (GLD only).** All 4 runnable validators pass comfortably. Scope
limited to GLD — SLV and crypto both rejected (SLV lacks gold's clean
opportunity-cost-of-zero-yield mechanism at the grid stage; crypto has no
comparable mechanism at all). Strongly regime-dependent (low/mid-vol edge,
weak in high-vol terciles) — a future loop should not assume this holds
during acute volatility spikes.

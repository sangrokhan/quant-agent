# Double Bottom (W-pattern) Neckline Breakout — QQQ/SPY/BTC/ETH

**Hypothesis:** Per https://www.investopedia.com/terms/d/doublebottom.asp,
a double-bottom W-pattern (two lows within a few percent of each other,
separated by an intermediate rebound high, "the neckline") signals a
downtrend reversal; source's own stated rule: "A long position is
recommended on a daily close above the first rebound's high, with a stop
loss at the pattern's second low." First chart-pattern strategy in this
repo requiring an explicit *second* confirmed low near the first (distinct
from the already-tested Turtle Soup single-swing fade, 2026-09-04-076).

Best config from grid search: `low_similarity_pct=0.03, max_pattern_bars=80,
target_mult=1.5` (pivot_window=5, min_pattern_bars=10, max_hold_days=30
held fixed).

## Single-config validator results (best config)

| Validator | QQQ | SPY |
|---|---|---|
| sharpe_ratio | **FAIL** 0.031 (thr 1.0) | **FAIL** 0.726 (thr 1.0) |
| max_drawdown | **FAIL** 0.315 (thr 0.25) | pass 0.182 (thr 0.25) |
| transaction_cost_survival (10bps/trade, 28-31 trades) | **FAIL** -0.011 net Sharpe (thr 0.5) | pass 0.662 (thr 0.5) |
| walk_forward (4-split manual date-slice, vbt RangeSplitter broken per prior known scaffold bug) | **FAIL** 0.50 pass-fraction (thr 0.75) | near-miss-pass 0.75 pass-fraction (thr 0.75) |

QQQ fails decisively across the board. SPY is a partial near-miss (3/4
validators pass) but Sharpe itself still fails threshold on the primary
metric.

## Step 6 grid summary (param_grid: low_similarity_pct∈{0.03,0.05},
max_pattern_bars∈{40,80}, target_mult∈{1.0,1.5}; symbols QQQ/SPY (equity),
BTC/USDT+ETH/USDT (crypto); vol_regime_splits=3)

- **pass_fraction: 0.156** (15/96 cells)
- by_asset_class: equity 15/48 passed, **crypto 0/48 passed** (no edge on
  crypto at all)
- by_vol_regime: low 10/32, mid 5/32, **high 0/32** (only survives in
  calm markets, exactly the regime this pattern is least useful in)
- best_cell: SPY, low-vol regime, Sharpe 1.68 (best config above)
- worst_cell: QQQ, high-vol regime, Sharpe -0.74

## Decision: REJECTED

Full-sample Sharpe fails on both equities at the best grid config (QQQ
decisively, SPY a near-miss but still below threshold), crypto shows zero
edge across the entire 48-cell crypto grid, and the strategy only clears
the bar in low-vol regimes — a narrow, non-robust edge. Not accepted.

**Notes for future loops:** SPY's low-vol-regime cells look genuinely
promising (Sharpe 1.68 best cell, MDD/TC-survival both pass) — a
volatility-regime-gated variant (only trade the pattern when in a
low-realized-vol regime, mirroring 2026-09-03-001's BB mean-reversion
gate) might rescue this on SPY specifically, but QQQ and crypto show no
underlying edge to rescue regardless of regime filtering.

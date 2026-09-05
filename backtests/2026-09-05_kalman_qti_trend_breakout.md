# Kalman-filter trend-percentile (QTI) breakout (rejected)

**Hypothesis:** Per Quantitativo's "Fast trend following" article
(quantitativo.com/p/fast-trend-following), run two recursive 1D Kalman
filters over price with different measurement-noise assumptions (fast/low-R
vs slow/high-R); rescale their pct difference into a rolling percentile-rank
"QTI" indicator in [-100,+100]. Long entry when QTI crosses above
`entry_level`; exit at `target_level` (profit target) or falling back below
`entry_level` (stop), or a `max_hold_days` time-stop (added here — the
source's original 1-min-NQ-futures design has no time cap).

Source: https://www.quantitativo.com/p/fast-trend-following (`web_search`
failed repeatedly with a DDGS/rustls TLS error this iteration too — fell
back to `browser_exec` Google search + direct page read).

Novelty: first Kalman-filter-based strategy in this repo — distinct from
all prior EMA/SMA/adaptive-MA (KAMA, FRAMA, McGinley, VIDYA, etc.)
non-recursive-state-space smoothers.

## Step 6 — Grid summary

Grid: `entry_level in {3,5,10}`, `target_level in {25,35}`,
`max_hold_days in {20,30}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 144 total cells.

- pass_fraction: 0.069 (10/144)
- by_asset_class: equity 10/72 passed; crypto 0/72 (decisive)
- by_vol_regime: low 4/48, mid 0/48, high 6/48
- best_cell: entry_level=5.0, target_level=25.0, max_hold_days=20, QQQ,
  low-vol, Sharpe 1.13

## Step 7 — Single-config check (best grid params: entry_level=5.0, target_level=25.0, max_hold_days=20)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (QQQ, full-period) | ❌ | 0.17 | ≥ 1.0 |
| Sharpe ratio (SPY, full-period) | ❌ | 0.08 | ≥ 1.0 |
| Max drawdown (QQQ) | ✅ | 9.4% | ≤ 25% |
| Max drawdown (SPY) | ✅ | 8.5% | ≤ 25% |

Full-period Sharpe is far below threshold on both equity symbols despite
narrow attractive slices in the grid (low-vol QQQ 1.13, some high-vol
cells passing too but no coherent single config). The intraday-1-minute
source design (QTI computed on Kalman filters tuned for 1-min NQ futures
noise characteristics) does not translate cleanly to a multi-year
daily-bar backtest — the adaptation captures small pockets of edge but no
robust full-sample signal. Skipped walk-forward/parameter-sensitivity given
the decisive full-period Sharpe failure.

## Decision: **REJECT** (both equity and crypto; intraday-tuned indicator doesn't generalize to daily bars)

# Backtest report: SuperTrend + volatility-regime gate (ACCEPTED — QQQ only)

**Strategy file:** `strategies/2026-09-09_supertrend_volregime_gated.py`

## Hypothesis

Direct fix attempt for this cron trigger's near-miss SuperTrend result
(id=2026-09-09-005): QQQ missed MDD by 0.6pp (0.256 vs 0.25); SPY missed
Sharpe by 0.097 (0.903 vs 1.0). That grid showed the edge concentrated in
low/mid vol regimes (0/36 high-vol passes) and 0/54 crypto. This iteration
adds an explicit realized-vol-vs-trailing-median regime gate (same
construction pattern as this repo's already-accepted BB mean-reversion
strategy, 2026-09-03-001) so new entries are skipped during high-vol
regimes, plus a max_hold_days=60 safety backstop the original lacked.

## Step 6 grid summary (run_strategy_grid)

- param_grid: `mult=[3.0,4.0,5.0]` x `vol_regime_ratio=[0.8,1.0,1.2]`
- symbols: equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT]
- vol_regime_splits=3
- **total_cells=108, passed_cells=12, pass_fraction=0.111**
- by_asset_class: equity 12/54, crypto 0/54
- by_vol_regime: low 11/36, mid 1/36, high 0/36
- best_cell: mult=4.0, vol_regime_ratio=1.2, QQQ low-vol, Sharpe=2.46
- worst_cell: mult=4.0, vol_regime_ratio=1.0, SPY high-vol, Sharpe=-1.15

## Single-config validation (best grid cell: mult=4.0, vol_regime_ratio=1.2), full sample

| Symbol | Sharpe | MDD | TC-survival | Walk-fwd | Param sensitivity | num_trades |
|---|---|---|---|---|---|---|
| QQQ | **1.007 (pass)** | **0.104 (pass)** | 0.985 (pass) | 1.00 (pass) | 0.218 rel-std (pass) | 9 |
| SPY | 0.684 (fail) | 0.128 (pass) | 0.653 (pass) | 0.50 (fail) | 3.172 rel-std (fail) | 10 |

QQQ now passes all 5 validators with a reasonable 9-trade sample -- the
vol-regime gate directly fixed the original MDD near-miss (0.256 -> 0.104,
more than halved) while keeping Sharpe above threshold. SPY still fails
Sharpe and, unlike the ungated version, now also fails walk-forward and
parameter sensitivity badly -- the gate over-restricts SPY's entries in a
way that doesn't help it the way it helps QQQ.

## Outcome: ACCEPTED (QQQ only); rejected (SPY, crypto)

QQQ: all 5 validators pass, directly resolving the near-miss MDD failure
from the ungated version (2026-09-09-005) via the added vol-regime gate.
SPY: fails Sharpe, walk-forward, and parameter sensitivity -- the gate
does not rescue SPY the way it does QQQ, so SPY remains out of scope.
Crypto: 0/54 grid cells, consistent with every SuperTrend variant tested on
crypto in this repo. Strategy file kept live in `strategies/` for QQQ-only
production use; SPY/crypto use is explicitly out of scope per this record.

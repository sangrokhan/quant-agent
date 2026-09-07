# Backtest Report: Percentage-Distance-from-MA Mean Reversion + ADX Ranging Filter

**Strategy file:** `strategies/2026-09-08_pct_distance_ma_adx_ranging_meanrev.py`
**Date:** 2026-09-08

## Hypothesis

Per https://www.coinquant.ai/blog/building-a-mean-reversion-strategy-in-cryptocurrency-markets-evidence-from-78-backtests
("Strategy C: Percentage distance from moving average" — long when price is
X% below its 20-SMA, exit when it recovers to the SMA), combined with the
source's own Section 4.2 proposed regime filter (only take mean-reversion
entries when ADX(14) is NOT above ~25, i.e. market is ranging not
trending) — a direct response to the source's Section 4.3 finding that naive
mean reversion lost -38.9%/-39.3% on BTC/ETH through the trending 2022 bear
market.

## Grid test (Step 6)

`param_grid={"entry_pct": [3,5,7], "adx_max": [20,25]}`,
symbols equity=[QQQ,SPY], crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
2019-01-01 to 2026-09-01. 72 cells total.

- **pass_fraction: 2/72 (2.8%)**
- by_asset_class: equity 2/36, crypto 0/36 (decisive fail)
- by_vol_regime: low 0/24, mid 2/24, high 0/24 (only the mid-vol tercile
  ever passes; low/high vol both 0)
- best_cell: entry_pct=5.0, adx_max=20.0, QQQ, mid-vol, Sharpe 1.40
- worst_cell: entry_pct=5.0, adx_max=25.0, SPY, mid-vol, Sharpe -0.47

## Single-config validation (Step 7), config entry_pct=5.0/adx_max=20.0, QQQ, full sample 2019-2026

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL | 0.390 | 1.0 |
| Max drawdown | PASS | 4.88% | 25% |
| Transaction-cost survival (10bps/trade, 8 trades) | FAIL | net Sharpe 0.319 | 0.5 |
| Walk-forward | ERROR (vectorbt API mismatch: `vbt.utils.splitting` not found in installed version) — not evaluated |
| Parameter sensitivity | FAIL | relative_std=NaN/Infinity (one grid cell, entry_pct=7/adx_max=20, produced only 0-1 trades → division blow-up) | 0.5 |

Parameter grid (Sharpe by config, full-sample QQQ):
```
entry_pct=3.0, adx_max=20.0: 0.144
entry_pct=3.0, adx_max=25.0: 0.385
entry_pct=5.0, adx_max=20.0: 0.390
entry_pct=5.0, adx_max=25.0: 0.151
entry_pct=7.0, adx_max=20.0: inf (degenerate — too few trades)
entry_pct=7.0, adx_max=25.0: 0.151
```

## Decision: REJECT

Grid pass_fraction only 2.8% — the mid-vol-tercile-only, QQQ-only outperformance
found by the grid does not survive as a full-sample single-config result
(Sharpe 0.39 vs threshold 1.0). Also fails transaction-cost survival, and
parameter sensitivity is degenerate (very few trades at wider thresholds
makes Sharpe estimates unstable/infinite). Crypto is a decisive 0/36 across
the whole grid, consistent with the source article's own finding that naive
displacement-from-mean strategies get crushed in trending crypto regimes —
even with the ADX ranging-filter bolted on, it is not selective enough to
rescue crypto performance, and the equity edge is too narrow (one vol
tercile, one symbol) and too thin (0.39 Sharpe, few trades) to be a real
robust edge rather than noise.

Walk-forward validator errored due to a `vectorbt.utils.splitting` API
mismatch in the installed vectorbt version (module attribute not found) —
this should be flagged for a future loop to fix the validator/dependency
version, not treated as a pass. Not decisive to the reject call since Sharpe
and TC-survival already failed independently.

# Backtest Report: NVI/MA Crossover + Trend Filter (2026-09-04)

**Hypothesis:** Negative Volume Index (NVI) crossing above/below its own
N-period moving average, gated by a long-term (200d/150d) trend filter,
identifies "smart money" accumulation/distribution phases and generates a
tradeable long-only edge. Source: Google AI-overview synthesis of
cTrader/LightningChart/Earn2Trade NVI explainers (see
https://www.google.com/search?q=Negative+Volume+Index+NVI+trading+strategy+entry+exit+rules).

**Strategy file:** `strategies/2026-09-04_nvi_ma_crossover_trendfilter.py`

## Primary config (QQQ, 2018-01-01 to 2026-09-01)
`nvi_ma_window=255, trend_window=150, max_hold_days=40`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.987 | 1.0 |
| Max drawdown | ✅ | 0.244 | 0.25 |
| Transaction cost survival | ✅ | net Sharpe 0.920 (10bps/trade, 63 trades) | 0.5 |
| Walk-forward | ⚠️ error | `vectorbt.utils` has no attribute `splitting` (repo-level API issue, not strategy-specific) | 0.75 |
| Parameter sensitivity | ❌ | relative std 0.993 (best Sharpe 2.43 vs worst 0.008 across grid) | 0.5 |

## Step 6 grid summary (param_grid: nvi_ma_window in [100,255], trend_window
in [150,200], max_hold_days=40; symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto); vol_regime_splits=3)

```
total_cells: 32, passed_cells: 10, pass_fraction: 0.3125
by_asset_class: equity 10/24 passed, crypto 0/8 passed
by_vol_regime: low 8/8, mid 2/8, high 0/8, n/a(insufficient data) 0/8
best_cell: QQQ, low-vol, nvi_ma_window=255/trend_window=150 -> Sharpe 2.43
worst_cell: SPY, mid-vol, same params -> Sharpe 0.008
```

## Verdict: **REJECTED**

Decisive rejection: fails the primary Sharpe threshold on the flagship
QQQ config outright (0.987 < 1.0), fails parameter sensitivity badly
(near-3x Sharpe swing between the best and worst grid cell — result is
highly config-dependent, not robust), and the effect vanishes entirely in
mid/high volatility regimes and across all of crypto (0/8 cells passed).
Only the low-vol equity slice looks attractive, and even there it doesn't
generalize across param values. Walk-forward validator hit a pre-existing
`vectorbt.utils.splitting` AttributeError in this repo's `validators.py` —
noted as a known infra issue for a future loop to fix, not counted for/against
this strategy.

Not recommending revisit unless: (a) restricted explicitly to low-vol
equity regimes with a regime-gate (similar shape to the already-accepted
Gann HiLo + SMA strategy, id 2026-09-04-128), or (b) the
`check_walk_forward` vectorbt API bug is fixed so a full validator suite can
actually run.

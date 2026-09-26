# Backtest Report: RVOL Exhaustion-Climax Reversal with Delayed Confirmation

**Strategy file:** `strategies/2026-09-27_rvol_exhaustion_confirmation_reversal.py`
**KB entry:** `2026-09-27-004` (rejected)

## Hypothesis

Per a Google AI-overview synthesis of ChartSchool/TradeAlgo/ChartsWatcher
RVOL-spike-reversal sources: an exhaustion bar with RVOL (volume / rolling
average volume) >= 4.0 at a new N-bar low, followed by a SEPARATE
confirmation bar closing bullish, followed by entry at the open of the
THIRD bar, with a stop 1-1.5% beyond the climax bar's low. Distinct from
this repo's many prior climax/exhaustion entries via the specific 4.0x
RVOL threshold and the mandatory two-bar-delayed confirmation-then-entry
sequencing (all prior entries enter same-bar or next-bar).

## Grid test summary (rvol_threshold in {3,4,5} x max_hold_days in {10,20,30} x equity/crypto x 3 vol terciles)

```
total_cells: 108
passed_cells: 0
pass_fraction: 0.0
by_asset_class: equity 0/54, crypto 0/54
by_vol_regime: low 0/36, mid 0/36, high 0/36
best_cell: SPY, high-vol, rvol_threshold=3.0/max_hold_days=10, Sharpe=-0.411 (negative)
```

## Signal-sparsity diagnostic (rvol_threshold=3.0, most permissive tested config)

| Symbol | Trades (full sample 2018-2026) |
|---|---|
| QQQ | 0 |
| SPY | 1 |
| BTC/USDT | 0 |
| ETH/USDT | 1 |

## Decision: REJECTED (decisive, signal starvation)

The compound condition (new N-bar low AND RVOL>=3-5x AND large-range bar
AND a separate bullish confirmation bar the very next day) essentially
never co-occurs on daily-bar OHLCV for these 4 liquid symbols -- 0-1 trades
across the entire 2018-2026 sample even at the most permissive threshold
tested (RVOL>=3.0). This confirms the source's own construction is
designed for intraday/5-minute charts (where RVOL spikes to 400%+ are far
more common due to session-relative volume baselines) and does not
transfer to a daily-bar backtest without a fundamentally looser threshold
that would abandon the source's own defining "exhaustion" numeric
criterion. No further validators were run given the 0/108 grid result and
near-zero trade counts.

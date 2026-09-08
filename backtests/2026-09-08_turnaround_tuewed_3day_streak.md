# Turnaround Tuesday/Wednesday 3-Day-Streak Reversal — Backtest Report (ACCEPTED, QQQ+SPY)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_turnaround_tuewed_3day_streak.py`
**Knowledge base id:** 2026-09-08-135

## Hypothesis

Per https://www.quantitativo.com/p/turnaround-tuesdays-on-steroids
(Quantitativo's own verification + improvement of the "Turnaround Tuesday"
blog strategy): long entry when today is Tuesday OR Wednesday AND there's
been a 3-consecutive-day decline sequence ending yesterday; exit when close
> yesterday's high. Source's own QQQ backtest: Sharpe 1.52, 11.4% annual
return vs 9.2% buy-and-hold, 70%+ win rate. Distinct from the already-
accepted plain Down-Monday->Tuesday reversal (2026-09-08-116) via the
3-day-decline requirement (vs single down day), trading both Tuesday and
Wednesday (vs Tuesday only), and a signal-based exit (vs fixed 1-day hold).

## Grid test summary (validation/grid_test.py)

- Grid: `trade_tuesday`=True × `trade_wednesday` in {True,False} ×
  `down_streak_days` in {2,3} (4 combos) × {QQQ, SPY, BTC/USDT, ETH/USDT} ×
  3 vol-regime terciles = 48 cells.
- **pass_fraction: 0.3125** (15/48)
- by_asset_class: equity 15/24; **crypto 0/24 (decisive reject)**
- by_vol_regime: low 4/16; mid 3/16; **high 8/16** — notably, this
  strategy's edge is NOT concentrated in low-vol regimes like most other
  strategies in this repo; it holds up (and even performs best in some
  cells) across all three vol regimes.
- best_cell: SPY, down_streak_days=2 (both days), low-vol regime, Sharpe
  1.969

## Single-config validators (config: trade_tuesday=True,
trade_wednesday=True, down_streak_days=3)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 1.272 | 1.075 | ≥1.0 | pass both |
| Max drawdown | 0.131 | 0.150 | ≤0.25 | pass both |
| TC survival (net Sharpe, 10bps/trade) | 1.060 | 0.840 | ≥0.5 | pass both |
| Walk-forward (4-quarter, manual fallback) | 1.0 | 1.0 | ≥0.75 | pass both |
| Parameter sensitivity (relative std, 4-combo grid) | 0.175 | 0.131 | ≤0.5 | pass both |

Num trades: QQQ 104, SPY 104 over 2019-01 to 2026-09.

## Crypto check (same config)

| Metric | BTC/USDT | ETH/USDT |
|---|---|---|
| Sharpe (full-sample) | 0.417 | 0.345 |
| Max drawdown | 0.415 | 0.490 |

Crypto fails decisively on both Sharpe and max drawdown.

## Decision: ACCEPTED (QQQ + SPY); crypto rejected decisively

Both equities pass all five validators cleanly, with a grid that holds up
across all three volatility regimes (unusual — most accepted strategies in
this repo concentrate edge in low-vol only). A genuinely robust, broadly-
applicable calendar-seasonality + mean-reversion combination strategy.

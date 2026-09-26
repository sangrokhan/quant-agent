# Backtest Report: MACD-V Extreme-Oversold Re-entry

**Strategy file:** `strategies/2026-09-26_macdv_extreme_oversold_reentry.py`
**KB id:** 2026-09-26-070
**Outcome:** REJECTED (decisive)

## Hypothesis

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/macd-v
(Alex Spiroglou 2022) — the "seven core momentum stages" table gives an
exact numeric extreme "Risk (oversold)" threshold: MACD-V < -150. Entry
fires when MACD-V crosses back above -150 (exits the extreme oversold
zone), betting on a mean-reversion rebound from an extreme momentum
trough, gated by close > SMA(trend_window). Exit on MACD-V re-entering the
oversold zone, crossing into overbought (>150), or a time-stop.

Distinct from this repo's 3 prior MACD-V entries (2026-09-06-094 Rebounding-
zone crossover, 2026-09-12-155 Rallying-zone breakout, 2026-09-14-141
continuous sizing dial) — none used the -150 extreme threshold itself as
the entry trigger.

## Grid summary (Step 6)

`param_grid={oversold_level:[-200,-150,-100], trend_window:[100,200]}`,
symbols equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
72 total cells, 2016-01-01 to 2026-09-01.

| Metric | Value |
|---|---|
| pass_fraction | **0.0 (0/72)** |
| by_asset_class | equity 0/36, crypto 0/36 |
| by_vol_regime | low 0/24, mid 0/24, high 0/24 |
| best_cell | QQQ, oversold_level=-100, trend_window=100, high-vol tercile, Sharpe 0.881 (still below threshold) |
| worst_cell | SPY, oversold_level=-100, trend_window=200, high-vol tercile, Sharpe -1.057 |

Zero passing cells anywhere in the grid.

## Single-config validation (Step 7) — best-cell params, full sample, QQQ

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.693 | ≥ 1.0 |
| Max drawdown | PASS | 0.021 | ≤ 0.25 |
| Transaction cost survival | PASS | net Sharpe 0.673 (2 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken, established repo workaround) | **FAIL** | 1/4 splits positive (0.25) | ≥ 0.75 |

Again an extremely sparse signal (only 2 trades over the ~10.7yr QQQ full
sample using the oversold_level=-100 relaxation) — the genuine -150 extreme
threshold from the source is rarer still, and relaxing it to -100 to get
any trades at all still produces a below-threshold Sharpe and fails
walk-forward decisively (1/4 splits positive).

## Decision

**Reject (decisive).** The extreme-oversold re-entry framing does not
survive: 0/72 grid cells passed, and the full-sample confirmation fails
Sharpe and walk-forward even at the best (most relaxed) grid parameters.
Strategy file retained in `strategies/` as a rejected-attempt record (not
live).

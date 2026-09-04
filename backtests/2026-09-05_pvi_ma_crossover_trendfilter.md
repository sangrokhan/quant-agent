# Backtest Report: PVI MA-crossover + trend filter (2026-09-05)

**Hypothesis:** Positive Volume Index (PVI) — cumulative sum of price % change
on volume-INCREASE days only (mirror of the previously-tested NVI, which
uses volume-decrease days) — crossing above its own N-period moving average
signals a long entry, confirmed by close above a long-term trend MA; exit on
reverse crossover, trend-filter break, or a max-hold time-stop.

**Sources:**
- https://www.tradingview.com/script/2OWFFJv3-Positive-Volume-Index-Backtest/
  (HPotter's PVI/NVI script description: formula and crossover-vs-own-MA
  convention)
- https://pinescriptforge.com/nq/positive-volume-index/backtest (search
  snippet only; page didn't render usable content live — confirms canonical
  255-period SMA crossover rule)

**Novelty:** distinct from 2026-09-04-139 (NVI+trend-filter, accepted SPY
only) — opposite volume-day condition (increase vs decrease), tested as its
own hypothesis rather than assumed to mirror NVI's result.

## Grid test (validation/grid_test.py)

- param_grid: `pvi_ma_window` in {50, 150, 255}, `trend_window` in {100, 200},
  `max_hold_days` in {30, 40}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3 (low/mid/high realized-vol terciles)
- total_cells = 144, passed_cells = 19, **pass_fraction = 13.2%**
- by_asset_class: equity 19/72 passed, crypto 0/72 passed
- by_vol_regime: low 8/48, mid 11/48, high 0/48 (high-vol regime never passes)
- best_cell: QQQ, pvi_ma_window=50, trend_window=100, max_hold_days=30,
  low-vol regime, Sharpe 2.72
- worst_cell: QQQ, pvi_ma_window=150, trend_window=200, max_hold_days=30,
  high-vol regime, Sharpe -1.17
- Per-(params,symbol) pass rates (of 3 vol-regime cells each), best config
  (pvi_ma_window=50, trend_window=100, max_hold_days=30): QQQ 2/3
  (avg Sharpe 1.27), SPY 1/3 (avg Sharpe 0.42), BTC/USDT 0/3 (avg Sharpe
  0.30), ETH/USDT 0/3 (avg Sharpe 0.19).

## Single-config validators (best config: pvi_ma_window=50, trend_window=100,
max_hold_days=30, QQQ, full 2019-01-01..2026-09-01 sample)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.138 | >= 1.0 | PASS |
| Max drawdown | 0.120 | <= 0.25 | PASS |
| Transaction-cost survival (10bps/trade, 44 trades) | 1.055 net Sharpe | >= 0.5 | PASS |
| Parameter sensitivity (pvi_ma_window in {50,150,255}, Sharpes 1.27/0.39/0.57) | relative_std 0.511 | <= 0.5 | **FAIL** (near-miss) |
| Walk-forward | skipped | n/a | vectorbt installed version has no `vbt.utils.splitting.RangeSplitter` (known repo issue, previously logged) |

## Decision: REJECTED (QQQ near-miss; SPY/crypto decisively weaker)

Parameter sensitivity fails narrowly (0.511 vs 0.5 threshold) — Sharpe drops
sharply as `pvi_ma_window` grows from 50 to 150/255, meaning the edge is
concentrated in a narrow, fast-responding parameter region rather than
holding broadly. Combined with SPY only passing 1/3 vol-regime cells and
crypto failing all cells (0/72), this does not clear the bar for acceptance
even though the single best QQQ config numerically passes Sharpe/MDD/TC.

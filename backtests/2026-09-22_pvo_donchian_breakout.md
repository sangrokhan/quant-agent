# Backtest report: PVO-Confirmed Donchian Breakout (REJECTED, QQQ)

**Strategy file:** `strategies/2026-09-22_pvo_donchian_breakout.py`
**Hypothesis id:** 2026-09-22-111
**Source:** StockCharts ChartSchool, https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/percentage-volume-oscillator-pvo (own disclosed PVO formula and "validating breaks" volume-confirmation heuristic).

## Hypothesis

First PVO-based strategy in this repo. Donchian-style breakout (close > rolling N-day high) confirmed by positive+rising PVO (crossing above its own signal line, i.e. above-average and increasing volume per the source's own "a resistance break on expanding volume shows more buying interest" heuristic). Exit on Donchian-low breakdown or a max holding period.

## Step 6 grid summary (breakout_window in {15,20,30} x max_hold_days in {15,20,30}, 2019-01-01..2026-09-01, vol_regime_splits=3, symbols QQQ/SPY/BTC-USDT/ETH-USDT)

- **total cells:** 108, **passed:** 46, **pass_fraction: 0.426**
- **by_asset_class:** equity 27/54; crypto 19/54
- **by_vol_regime:** low 32/36; mid 13/36; high 1/36 (breakout strategies structurally struggle in high-vol whipsaw regimes)
- **best cell:** ETH/USDT, breakout_window=15/max_hold_days=15, mid-vol regime, Sharpe 2.28
- QQQ at breakout_window=20/max_hold_days=20 passed 2/3 vol-regime grid slices, looked like the best equity candidate.

## Step 7 single-config validation (QQQ, breakout_window=20/max_hold_days=20, full 2019-2026 sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.57 | >= 1.0 |
| Max drawdown | pass | 0.205 | <= 0.25 |
| Transaction cost survival (10bps/trade, 40 trades) | **FAIL** | net Sharpe 0.48 | >= 0.5 |
| Walk-forward (4 splits) | pass (borderline) | 0.75 (3/4 positive: -0.34, 0.41, 0.99, 1.71) | >= 0.75 |
| Parameter sensitivity (9-cell QQQ grid) | pass | relative_std 0.120 | <= 0.5 |

Full-sample Sharpe and transaction-cost-survival both fail despite passing 2/3 grid vol-regime slices individually and passing max-drawdown/walk-forward/parameter-sensitivity -- too few trades (40 over 7.5yr) combined with a weak first walk-forward split drag down the full-sample average below the low-vol-slice-only picture the grid presented.

## Decision: REJECTED

Fails 2 of 5 full-sample validators (Sharpe, transaction-cost survival) on its best grid-selected equity config. Strategy file and this report kept as a record of a rejected attempt. The underlying PVO-confirmation mechanic showed promise on crypto (ETH/USDT mid-vol Sharpe 2.28 in the grid) that a future iteration could explore as a crypto-focused follow-up rather than re-deriving the whole mechanic.

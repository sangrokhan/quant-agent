# Backtest Report: Percent B + Money Flow Index Dual-Thrust Momentum Confirmation

**Strategy file:** `strategies/2026-09-05_percentb_mfi_dual_thrust.py`
**Knowledge base id:** 2026-09-05-011

## Hypothesis

John Bollinger's "Percent B and Money Flow" system (per StockCharts
ChartSchool's disclosure of his book "Bollinger on Bollinger Bands"):
buy when %B moves above 0.80 AND MFI moves above 80 (simultaneous
strong-upside-thrust confirmation from both price-location and volume);
sell when %B moves below 0.20 AND MFI moves below 20. A momentum/
trend-start system, explicitly distinct from Bollinger %B mean-reversion
(id=2026-09-04-107, buys BELOW the lower band) and standalone MFI
oversold-bounce (id=2026-09-04-033, buys on MFI recovery from oversold).

Source: https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/percent-b-money-flow

## Grid test summary (Step 6)

- `param_grid`: `bb_window` in {15, 20}, `mfi_window` in {10, 14}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **96 total cells, 16 passed, pass_fraction = 0.167**
- By asset class: equity 16/48, crypto 0/48
- By vol regime: low 16/32, mid 0/32, high 0/32 (again, low-vol-tercile-only)
- Best cell: bb_window=20, mfi_window=14, max_hold_days=20, QQQ, low-vol, Sharpe 3.07

## Single best-config validators (Step 7)

Config: `bb_window=20, mfi_window=14, max_hold_days=20`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.011 | 0.406 | ≥ 1.0 | QQQ ✅ (marginal, 13 trades) / SPY ❌ |
| Max drawdown | 0.127 | 0.116 | ≤ 0.25 | ✅ / ✅ |
| Net Sharpe after costs (10bps/trade) | 0.977 | 0.354 | ≥ 0.5 | QQQ ✅ / SPY ❌ |
| Num trades | 13 | 16 | — | thin samples |
| Parameter sensitivity (bb_window x mfi_window sweep, QQQ, relative_std) | 0.512 | — | ≤ 0.5 | ❌ (decisive fail) |

QQQ's Sharpe sweep across {bb=15,mfi=10: 0.30; bb=15,mfi=14: 1.07;
bb=20,mfi=10: 0.38; bb=20,mfi=14: 1.01} shows the result collapses to
well below threshold at 2 of 4 nearby parameter combos.

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

QQQ's nominal Sharpe pass (1.011) is on only 13 trades over 7.5yr and
decisively fails parameter sensitivity (relative_std 0.512 > 0.5
threshold) — collapsing to 0.30-0.38 at nearby bb_window/mfi_window
combos, indicating an overfit artifact rather than a robust edge (same
lesson as Woodie's CCI ZLR, 2026-09-05-007). SPY fails outright (Sharpe
0.406, net-of-cost 0.354). Crypto rejected decisively (0/48 grid cells).

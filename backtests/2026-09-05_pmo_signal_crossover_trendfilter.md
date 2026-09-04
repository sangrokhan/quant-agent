# Backtest Report: DecisionPoint Price Momentum Oscillator (PMO) Signal-Line Crossover + Trend Filter

**Strategy file:** `strategies/2026-09-05_pmo_signal_crossover_trendfilter.py`
**Knowledge base id:** 2026-09-05-010

## Hypothesis

Carl Swenlin's DecisionPoint Price Momentum Oscillator (PMO): a
double-smoothed 1-period ROC oscillator. PMO Line crossing above its
10-period EMA Signal Line, gated by close > SMA(trend_window), signals a
long entry (analogous to a MACD signal-line crossover, per StockCharts
ChartSchool's explicit comparison). Exit on cross-down, trend-filter break,
or a max_hold_days time-stop.

Source: https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/decisionpoint-price-momentum-oscillator-pmo
(exact formula for PMO Line/Signal Line disclosed free).

First PMO strategy in this repo — distinct from MACD (plain EMA
difference) and PPO (id=2026-09-04-109, EMA-ratio construction); PMO uses
a custom double-smoothed 1-day-ROC-percentage construction.

## Grid test summary (Step 6)

- `param_grid`: `trend_window` in {150, 200}, `max_hold_days` in {20, 30}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **48 total cells, 8 passed, pass_fraction = 0.167**
- By asset class: equity 8/24, crypto 0/24
- By vol regime: low 8/16, mid 0/16, high 0/16 (equity passes ONLY in the low-vol tercile)
- Best cell: trend_window=200, max_hold_days=30, QQQ, low-vol, Sharpe 2.16

## Single best-config validators (Step 7)

Config: `trend_window=200, max_hold_days=30`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.718 | 0.424 | ≥ 1.0 | ❌ / ❌ |
| Max drawdown | 0.189 | 0.138 | ≤ 0.25 | ✅ / ✅ |
| Net Sharpe after costs (10bps/trade) | 0.609 | 0.250 | ≥ 0.5 | ✅ / ❌ |
| Num trades | 65 | 73 | — | — |

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

Full-sample Sharpe decisively fails on both QQQ (0.718) and SPY (0.424),
well below the 1.0 threshold, despite the grid's isolated low-vol-tercile
passes (best cell Sharpe 2.16). This is the same lesson recorded in
2026-09-05-006 (CFO) and elsewhere: per-vol-regime grid passes can mask a
genuinely weak full-sample edge when the strategy's edge is concentrated
in a narrow slice of the sample. Crypto also fails all 24 grid cells.

# 2026-09-08 Ehlers Cyber Cycle Zero-Line Crossover (SPY) — REJECTED

**Hypothesis:** John Ehlers' Cyber Cycle (Cybernetic Analysis for Stocks
and Futures, 2004), per the exact formula at
https://help.ctrader.com/indicators/built-in/oscillators/cyber-cycle/: a
4-bar weighted smoothing of median price feeds a 2-pole recursive filter
(parameterized by alpha, default 0.07) that isolates the cyclic component
with minimal lag. Long entry on the Cycle line's zero-line crossover
(source's own documented uptrend signal); exit on the Cycle crossing below
its own 1-bar-lagged Trigger line while still positive (Ehlers' own
earlier-turning-point construct), a fresh zero-line cross down, or a
max_hold_days time-stop.

Source: https://help.ctrader.com/indicators/built-in/oscillators/cyber-cycle/
(exact formula, alpha default, bootstrap formula for early bars, Trigger
construction). First Ehlers Cyber Cycle strategy in this repo -- distinct
from all other Ehlers-family strategies tested (Fisher Transform,
Instantaneous Trendline, Voss Predictive Filter, Trendflex/Reflex, Roofing
Filter, MESA MAMA/FAMA, Laguerre RSI, Even Better Sinewave, Ergodic
Oscillator) since Cyber Cycle's alpha-parameterized 2-pole recursive filter
is a unique construction among them.

## Grid test (Step 6)

`param_grid = {alpha: [0.05, 0.07, 0.10], max_hold_days: [10, 15, 20]}`,
`symbols = {equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Overall pass fraction: 20/108 (18.5%)**
- By asset class: equity 20/54, crypto 0/54 (decisive crypto rejection)
- By vol regime: low 12/36, mid 8/36, **high 0/36**
- Best cell: SPY, low-vol, `alpha=0.10, max_hold_days=10`, Sharpe 1.618
- Worst cell: QQQ, high-vol, `alpha=0.07, max_hold_days=15`, Sharpe -0.406

## Single-config validators (Step 7): SPY, alpha=0.10, max_hold_days=10, full sample 2019-2026

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL | 0.294 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 11.9% | ≤ 25% |
| Transaction cost survival (10bps/trade, 98 trades) | ❌ FAIL | net Sharpe 0.037 | ≥ 0.5 |
| Walk-forward (manual 4-equal-slice fallback) | ✅ PASS | 3/4 splits positive (75%) | ≥ 75% |
| Parameter sensitivity (9-point sweep: alpha×max_hold_days) | ✅ PASS | relative_std 0.364 | ≤ 0.5 |

98 trades over the full sample is very high turnover for a daily-bar
strategy — the zero-line crossover of a fast-reacting 2-pole recursive
filter fires often, and the marginal edge per trade doesn't survive
10bps/trade costs.

## Decision: REJECTED

Full-sample Sharpe fails decisively (0.294 vs 1.0) and transaction-cost
survival fails decisively (net Sharpe 0.037 vs 0.5) despite MDD/walk-forward
/param-sensitivity all passing. The grid's low-vol-only pass pattern (12/36
low, 8/36 mid, 0/36 high) is consistent with a narrow, high-turnover edge
that doesn't cover costs. Crypto rejected decisively (0/54). Left in
`strategies/` as a rejected record.

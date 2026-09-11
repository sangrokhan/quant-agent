# Bullish Hikkake Pattern — Backtest Report (2026-09-11)

## Hypothesis
Per QuantifiedStrategies.com's mechanical definition
(https://www.quantifiedstrategies.com/bullish-hikkake-pattern/ — no
numeric backtest stats disclosed on the page, only the pattern definition,
which is precise enough to implement): the Bullish Hikkake is an
inside-bar (harami) false-breakdown-then-reversal pattern. Sequence:
(1) an inside bar forms (day N contained within day N-1's range),
(2) a subsequent day breaks below the inside bar's low (fake breakdown,
traps bearish traders who short with stops above the inside bar's high),
(3) within a short confirmation window, close breaks back above the
inside bar's high, confirming the bullish signal and triggering the
trapped shorts' stop-covering. Source frames the causal mechanism as
"stop-hunt" short-covering fuel for the reversal move.

Source gave no numeric confirm-window/exit rule, so `confirm_window`
(days allowed between fake breakdown and confirming breakout) and
`max_hold_days` (fixed time-stop) were grid-tested as the tunable
parameters.

## Grid test (Step 6)
`param_grid`: confirm_window [2,3,5] x max_hold_days [5,10,20]; symbols
equity [QQQ, SPY] + crypto [BTC/USDT, ETH/USDT]; vol_regime_splits=3.
108 total cells.

- **pass_fraction: 0.093** (10/108)
- by_asset_class: equity 10/54 passed; **crypto 0/54** (decisive reject)
- by_vol_regime: low 8/36; mid 1/36; high 1/36 — edge almost entirely
  confined to the low-vol tercile
- best_cell: QQQ, confirm_window=5/max_hold_days=20, low-vol regime,
  Sharpe 2.33

## Single-config validation (Step 7) — best config: confirm_window=5,
max_hold_days=20, 2019-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.361 **FAIL** | 0.604 **FAIL** | >= 1.0 |
| Max Drawdown | 0.306 **FAIL** | 0.349 **FAIL** | <= 0.25 |
| Net Sharpe after 10bps/trade costs | 0.318 **FAIL** | 0.550 pass | >= 0.5 |
| Walk-forward pass fraction | 0.75 (3/4) pass | 0.75 (3/4) pass | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.306 pass | 0.587 **FAIL** | <= 0.5 |
| Trades | 47 | 48 | — |

## Decision: REJECT
Both QQQ and SPY fail decisively on Sharpe and max drawdown at the
grid-best config; the strong grid-cell Sharpe (2.33) is confined to a
narrow low-vol-regime slice and does not generalize to the full sample.
QQQ additionally fails net-of-cost Sharpe; SPY fails parameter
sensitivity (grid-best config is a fragile/cliff-edge point, not a robust
plateau). Crypto rejected decisively (0/54). The pattern's low signal
frequency (~47-48 trades over 8 years) also means the grid-best low-vol
cell's Sharpe 2.33 is statistically thin. Consistent with this repo's
broader finding that multi-bar candlestick reversal patterns (three
inside up/down, engulfing, etc.) rarely clear the Sharpe/MDD bar
standalone without a trend/regime filter.

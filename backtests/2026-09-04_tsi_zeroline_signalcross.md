# True Strength Index (TSI) zero-line + signal-line crossover — backtest report

**Strategy file:** `strategies/2026-09-04_tsi_zeroline_signalcross.py`
**Hypothesis id:** 2026-09-04-129

## Hypothesis

William Blau's True Strength Index (double-smoothed price-momentum
oscillator, r=25 long EMA / s=13 short EMA of momentum) with a signal line
(EMA(TSI,7)). Per
[enlightenedstocktrading.com](https://enlightenedstocktrading.com/true-strength-index/):
"Enter a long position when TSI crosses above the zero line ... Exit a
long trade when TSI crosses below the zero line." This test combines that
zero-line regime filter with the more responsive signal-line crossover as
entry/exit trigger: long entry on TSI crossing above signal AND TSI>0;
exit on TSI crossing below signal, TSI crossing below zero, or a
max_hold_days time-stop.

Source: https://enlightenedstocktrading.com/true-strength-index/ (via
browser_exec Google-search fallback after web_search's DDGS/Yahoo backend
returned a connection error).

## Grid summary (Step 6)

`r` in {20,25} x `s` in {10,13} x `max_hold_days` in {10,15}, symbols
QQQ/SPY/BTC/USDT/ETH/USDT, vol_regime_splits=3:

- 96 cells total, 8 passed (pass_fraction=0.083)
- by_asset_class: equity 8/48, crypto 0/48
- by_vol_regime: low 4/32, mid 0/32, high 4/32
- best_cell: r=25, s=13, max_hold_days=10, QQQ, low-vol, Sharpe=1.86
- worst_cell: r=25, s=13, max_hold_days=15, QQQ, high-vol, Sharpe=-1.33

## Primary config validators (r=25, s=13, signal_period=7, max_hold_days=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.197 **FAIL** | 0.057 **FAIL** |
| Max drawdown (<=0.25) | 0.097 PASS | 0.121 PASS |
| Net Sharpe after costs (>=0.5, 10bps/trade) | 0.080 **FAIL** (41 trades) | -0.127 **FAIL** (56 trades) |
| Walk-forward (4-split, >=0.75 pass_frac) | 0.50 **FAIL** | 0.75 PASS |
| Parameter sensitivity (rel.std<=0.5, r in {20,25}) | 0.102 PASS | 0.727 **FAIL** |

## Decision

**Reject (both QQQ and SPY).** Both fail Sharpe and TC-survival decisively;
QQQ also fails walk-forward, SPY also fails parameter-sensitivity. Grid
pass_fraction (8.3%) is the lowest tier for a trend/momentum-oscillator
family tested in this repo so far. Crypto rejected outright (0/48 cells).

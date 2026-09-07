# REX Oscillator Trend-Continuation Pullback — Backtest Report

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_rex_oscillator_pullback_continuation.py`
**Source:** https://www.quantifiedstrategies.com/rex-oscillator/ (REX
Oscillator formula and stated trend-continuation use case; numeric backtest
rule itself paywalled)

## Hypothesis

TVB = 3*Close - (Low+Open+High); REX = EMA(TVB, rex_period). Long entry when
close > SMA(trend_window) (uptrend) AND REX was negative within the recent
lookback (active pullback) AND REX crosses back above zero (pullback ending
per source's own description). Exit on REX crossing back below zero, trend
filter breaking, or a max_hold_days time-stop. Tested QQQ/SPY/BTC-USDT/ETH-USDT.

## Grid summary (Step 6)

`param_grid={rex_period: [14, 21], trend_window: [50, 100]}`,
`symbols={equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells=48, passed_cells=8, **pass_fraction=0.167**
- by_asset_class: equity 8/24, crypto 0/24 (decisive crypto rejection)
- by_vol_regime: low 6/16, mid 1/16, high 1/16
- by_symbol: QQQ 5/12, SPY 3/12
- best_cell: QQQ low-vol, rex_period=21/trend_window=50, Sharpe 1.49
- worst_cell: QQQ high-vol, rex_period=14/trend_window=50, Sharpe -1.21

## Single-config validation (Step 7): rex_period=21, trend_window=50

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.341 (FAIL) | 0.421 (FAIL) | >= 1.0 |
| Max drawdown | 0.189 (pass) | 0.117 (pass) | <= 0.25 |
| Net Sharpe after 10bps costs | 0.025 (FAIL) | 0.031 (FAIL) | >= 0.5 |
| Walk-forward (manual 4-split) | 0.50, 2/4 (FAIL) | 0.75, 3/4 (pass) | >= 0.75 |
| Parameter sensitivity (4-cell relative std) | 0.244 (pass) | 0.144 (pass) | <= 0.5 |

QQQ trades 162 times, SPY 172 times over the sample -- high turnover relative
to a ~7-year daily-bar backtest -- which crushes net-Sharpe after even modest
10bps transaction costs on both symbols. Full-sample Sharpe is also a clear
miss on both, well below the isolated best-cell Sharpe (1.49) that only
reflects the low-vol tercile.

## Decision: REJECTED (both QQQ and SPY; decisive, not a near-miss)

Both symbols fail full-sample Sharpe and net-Sharpe-after-costs decisively;
QQQ additionally fails walk-forward. Crypto rejected decisively (0/24). The
strategy's frequent zero-line crossovers (REX oscillates often even within
an established trend) produce too much churn for the underlying edge --
consistent with the source's own stated limitation that REX "can give false
signals a lot" and is intended primarily as an exit signal rather than a
standalone entry trigger. Not flagged for follow-up; the entry-side use case
appears weak as tested.

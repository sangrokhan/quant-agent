# Backtest report: Elder SafeZone Stop trend-following exit overlay

**Strategy file:** `strategies/2026-09-17_elder_safezone_stop_trend_exit.py`

## Hypothesis

Per Alexander Elder's SafeZone Stop (2002), confirmed via Google SERP
synthesis this iteration (QuantShare.com's own disclosed usage rule:
`sell = close < safezone(20, 2)`, lookback=20/coefficient=2 as source
defaults; corroborated by Wealth-Lab Wiki / TradingView SERP snippets:
"Long Stop = Previous Low - (Average Downside Noise x Multiplier)"),
operationalize SafeZone as a trailing STOP-LOSS overlay on a simple
SMA-crossover trend entry: enter long on close crossing above
SMA(entry_window); exit on close falling below the SafeZone trailing stop
level (average downside penetration of prior lows, scaled by `coefficient`)
or a max_hold_days backstop. First SafeZone entry in this repo (0 prior
matches in strategies_index.jsonl).

## Grid test summary (Step 6)

`param_grid={"entry_window": [10,20,30], "coefficient": [2.0,2.5,3.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 39, **pass_fraction: 36.1%**
- by_asset_class: equity 33/54; **crypto 6/54**
- by_vol_regime: low 23/36; mid 4/36; high 12/36
- best_cell: SPY, low-vol regime, entry_window=20/coefficient=3.0, Sharpe 2.44
- worst_cell: QQQ, high-vol regime, entry_window=10/coefficient=2.0, Sharpe -0.42

## Single-config validators (best grid config: entry_window=20, coefficient=3.0), full sample 2019-2026

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>=1.0) | pass 1.148 | pass 1.165 | **FAIL** 0.753 | **FAIL** 0.869 |
| Max Drawdown (<=0.25) | pass 0.178 | pass 0.131 | **FAIL** 0.623 | **FAIL** 0.653 |
| TC survival (net Sharpe >=0.5, 5bps/trade) | pass 1.077 (109 trades) | pass 1.066 (113 trades) | not run (decisive Sharpe/MDD fail) | not run |
| Walk-forward (4-split manual date-split fallback) | pass 1.00 (4/4 splits positive) | pass 1.00 (4/4 splits positive) | not run | not run |
| Parameter sensitivity (coefficient in [2.0..3.5], relative_std<=0.5) | pass 0.133 | pass 0.083 | not run | not run |

## Decision: ACCEPTED (equity QQQ + SPY only); REJECTED (crypto BTC/USDT, ETH/USDT)

Equity: all 5 validators pass cleanly on both QQQ and SPY with a shared
config (entry_window=20, coefficient=3.0) -- strong, non-fragile result
(walk-forward 4/4, parameter sensitivity relative_std <0.15 on both).
Crypto decisively rejected: Sharpe well below threshold and MDD 2.5x the
0.25 cap on both BTC/USDT and ETH/USDT -- the fixed max_hold_days=60
backstop combined with SafeZone's downside-noise-based stop (calibrated
implicitly for equity-scale daily noise) does not adapt to crypto's much
larger daily swings, letting drawdowns run far past the equity-calibrated
stop width. Scope recorded here for future loops: this SafeZone
trend-exit construction is an EQUITY-ONLY strategy as configured; a future
iteration could attempt a crypto-specific leverage-cap/coefficient
recalibration (the pattern that has rescued several other equity-only
near-misses in this repo) but that is out of scope for this iteration.

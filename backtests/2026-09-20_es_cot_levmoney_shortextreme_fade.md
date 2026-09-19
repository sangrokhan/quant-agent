# CFTC COT E-mini S&P 500 Leveraged-Money Short-Extreme Fade — Backtest Report

**Hypothesis:** E-mini S&P 500 futures leveraged-money net position (a
persistently net-short book) reaching an extreme low percentile (bottom
decile of trailing distribution, i.e. more short than usual) signals
maximal bearish crowding — contrarian bullish fade on SPY/QQQ. Fifth COT
strategy this cron trigger, fifth market (E-mini S&P 500 futures — first
use of equity-index-futures COT data in this repo; only 241 weekly rows
available, 2022-02 to present, since CFTC only began separately reporting
this specific TFF-classified market from that date).

**Sources:**
- https://www.google.com/search?q=S%26P+500+E-mini+futures+COT+asset+manager+positioning+extreme+trading+signal+rule (browser_exec Google SERP; CME Group's own COT whitepaper "E-mini S&P's the Ultimate Index?", modigin.com, thetrading.tools)
- https://publicreporting.cftc.gov/resource/gpe5-46if.json (`E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE` market, 241 weekly rows since 2022-02-08)

**Data:** SPY/QQQ daily OHLCV via `load_equity` (restricted to 2022-03 to 2026-09-18 to match COT data availability); BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {lookback_weeks: [26,52,78], low_pct: [0.05,0.10,0.15]}`,
`symbols = {equity: [SPY,QQQ], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 15, **pass_fraction: 0.139**
- by_asset_class: equity 12/54 passed (22%), crypto 3/54 passed (robustness-check-only)
- by_vol_regime: low 11/36, mid 4/36, high 0/36
- best_cell: lookback_weeks=26, low_pct=0.05, SPY, low-vol, Sharpe 1.58
- worst_cell: lookback_weeks=78, low_pct=0.15, BTC/USDT, mid-vol, Sharpe -1.94

## Primary-config validation (SPY, lookback_weeks=26, low_pct=0.05 — best equity cell)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period, 2022-03 to 2026-09) | 0.655 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.044 | ≤ 0.25 | PASS |
| Transaction cost survival (10bps/trade, 30 trades) | 0.466 net Sharpe | ≥ 0.5 | **FAIL** |
| Walk-forward (4 splits) | 2/4 positive (0.94, 2.07, -0.56, -0.15) = 0.5 | ≥ 0.75 | **FAIL** |
| Parameter sensitivity (9-cell sweep) | relative std 1.386 (Sharpe ranges from -0.29 to 0.66, sign-flipping) | ≤ 0.5 | **FAIL** |

## Decision: REJECTED

Sharpe fails, net-of-cost Sharpe fails, walk-forward fails (only 50%
positive, with the two most recent splits both negative — the signal
appears to have decayed or been an artifact of the short 2022-2023
sample), and parameter sensitivity fails decisively (Sharpe sign-flips
across nearby parameter values, relative std 1.39 vs 0.5 threshold) — the
short 241-week COT history for this market is likely insufficient to
establish a robust percentile-extreme signal. Strategy file and this
report kept as a record of a rejected attempt.

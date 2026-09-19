# CFTC COT Leveraged-Money Extreme-Positioning Fade — Backtest Report

**Hypothesis:** CME Bitcoin futures COT "Leveraged Money" net position
(long - short) sitting in the bottom decile of its trailing 3-year
(156-week) rolling distribution signals extreme short-crowding among
speculators, historically preceding mean-reverting upward price moves —
contrarian long-only fade. First use of CFTC COT data in this repo.

**Sources:**
- https://www.google.com/search?q=Commitment+of+Traders+report+extreme+net+speculator+positioning+trading+strategy+specific+rule (browser_exec Google SERP AI overview; TradeAlgo/FP Markets/Oanda summaries: 90th/10th percentile of 3-year net-position distribution as extreme threshold; Friday 3:30pm ET release with Tuesday cutoff data, ~3-day lag)
- https://publicreporting.cftc.gov/resource/gpe5-46if.json (CFTC Socrata public API, direct — confirmed BITCOIN futures COT weekly history available 2017-12-19 to present, 875 rows)

**Data:** BTC/USDT daily OHLCV (2019-01-01 to 2026-09-18) via `data/loaders.load_crypto`; CME Bitcoin futures weekly COT `lev_money_positions_long/short` fetched live from CFTC's Socrata endpoint.

## Grid test (equity + crypto, vol_regime_splits=3)

`param_grid = {lookback_weeks: [104,156,208], low_pct: [0.05,0.10,0.15]}`,
`symbols = {equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}` (equity legs
run the same BTC-COT-derived signal purely as an out-of-sample robustness
check, not because COT/equity-index-futures data was used).

- total_cells: 108, passed_cells: 14, **pass_fraction: 0.130**
- by_asset_class: equity 11/54 passed, crypto 3/54 passed
- by_vol_regime: low 12/36, mid 2/36, high 0/36
- best_cell: lookback_weeks=208, low_pct=0.15, SPY, low-vol regime, Sharpe 2.24
- worst_cell: lookback_weeks=208, low_pct=0.1, QQQ, mid-vol regime, Sharpe -0.60

Grid signal is noisy/regime-dependent and best cells cluster in equity
low-vol (spurious given the signal is BTC-COT-derived and equity was only
included as a robustness check, not a genuine hypothesis leg) — crypto,
the actual intended asset class, passes only 3/54 cells.

## Primary-config validation (BTC/USDT, lookback_weeks=104, low_pct=0.05 — best crypto cell from grid)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | 0.737 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.517 | ≤ 0.35 | **FAIL** |
| Transaction cost survival (10bps/trade, 64 trades) | 0.705 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward | not run — `vbt.utils.splitting.RangeSplitter` unavailable in installed vectorbt version (AttributeError); Sharpe/MDD already decisive fail | n/a | n/a |
| Parameter sensitivity (relative std across 6 nearby grid cells) | ~0.03 | ≤ 0.5 | PASS |

## Decision: REJECTED

Full-period Sharpe (0.737) and max drawdown (51.7%) both fail their
thresholds on the best-performing crypto grid cell; the earlier grid-cell
Sharpe of 1.19 was a favorable mid-vol-regime slice, not representative of
the full sample. Low overall pass_fraction (13%) confirms the signal does
not hold up broadly. Strategy file and this report kept as a record of a
rejected attempt — not live.

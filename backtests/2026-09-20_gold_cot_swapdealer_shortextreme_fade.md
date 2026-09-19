# CFTC COT Gold Swap-Dealer Short-Extreme Fade — Backtest Report

**Hypothesis:** Gold swap-dealer (bullion bank OTC-hedging) net position
reaching an even more extreme net-short level than usual (bottom decile
of trailing distribution) implies dealers are "tapped out" absorbing
client buying, a contrarian bullish tell — long GLD when Gold swap-dealer
net position percentile-ranks in the bottom 10-15% of its trailing
distribution. Ninth COT strategy this cron trigger; reuses Gold's dataset
(already used for -038) but a distinct COT category (swap dealer, not
non-commercial/leveraged-money).

**Sources:**
- https://www.google.com/search?q=GLD+gold+COT+swap+dealer+positioning+extreme+bullion+bank+trading+signal+rule (browser_exec Google SERP; silverdominion.com live commentary, cotinsight.com "Gold has an unusually important swap-dealer layer")
- https://publicreporting.cftc.gov/resource/72hh-3qpy.json (Disaggregated report, `GOLD - COMMODITY EXCHANGE INC.` market, `swap_positions_long_all`/`swap__positions_short_all` fields, 1058 weekly rows since 2006)

**Data:** GLD/SLV daily OHLCV via `load_equity`; BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {lookback_weeks: [104,156,208], low_pct: [0.05,0.10,0.15]}`,
`symbols = {equity: [GLD,SLV], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 11, **pass_fraction: 0.102**
- by_asset_class: equity 11/54 passed (20%), crypto 0/54 passed
- by_vol_regime: low 11/36, mid 0/36, high 0/36
- best_cell: lookback_weeks=208, low_pct=0.15, GLD, low-vol, Sharpe 3.97
- worst_cell: lookback_weeks=156, low_pct=0.05, ETH/USDT, low-vol, Sharpe -1.65

## Primary-config validation (GLD, lookback_weeks=208, low_pct=0.15 — grid's best cell)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | 0.545 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.170 | ≤ 0.25 | PASS |
| Transaction cost survival (10bps/trade, 37 trades) | 0.487 net Sharpe | ≥ 0.5 | **FAIL** |

## Decision: REJECTED

The favorable low-vol-regime cell (Sharpe 3.97) does not hold up over the
full sample (Sharpe 0.545, net-of-cost 0.487, both below threshold) — the
signal's apparent edge is concentrated in a narrow low-vol slice rather
than broadly present. Unlike -038's non-commercial trend-confirmation
signal (accepted, full-period Sharpe 1.006), the swap-dealer
extreme-percentile-fade framing does not transfer well to Gold. Strategy
file and this report kept as a record of a rejected attempt.

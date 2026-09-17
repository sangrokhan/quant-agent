# Backtest Report: SMA(High/Low) Breakout with EMA Trend Filter

**Strategy file:** `strategies/2026-09-17_sma_high_breakout_ema_trend.py`
**Source:** https://traders.com/documentation/feedbk_docs/2013/12/traderstips.html
(TASC December 2013 Traders' Tips, "Swing Trading With Three Indicators" by
Donald Pendergast; TradeStation EasyLanguage credited to Doug McCrary/
TradeStation Securities; read this iteration via `browser_exec` after
`web_search`/DDGS returned "No results found" for the search query).

## Hypothesis

A breakout of a short SMA-of-highs (plus a small buffer) gated by the prior
close being above a long EMA (trend filter) should mark higher-quality long
entries than an unconditional SMA-of-high breakout; exit when price falls
back below the SMA-of-lows. Distinct from repo's existing Donchian
breakout family (rolling MAX/MIN, not rolling AVERAGE of high/low).

## Grid test summary (Step 6)

`param_grid={"sma_length": [5,10], "ema_length": [30,50,100]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 72, **passed_cells:** 17, **pass_fraction:** 0.236
- **by_asset_class:** equity 13/36 (0.361), crypto 4/36 (0.111)
- **by_vol_regime:** low 15/24 (0.625), mid 2/24 (0.083), high 0/24 (0.0)
- **best_cell:** sma_length=5, ema_length=100, SPY, low-vol regime, Sharpe=3.00
- **worst_cell:** sma_length=10, ema_length=30, QQQ, high-vol regime, Sharpe=-0.81

Zero cells pass in the high-vol tercile across both asset classes -- a
strong signal this construction is fragile outside calm markets even before
looking at costs.

## Single-config validators (Step 7) — best grid config: sma_length=5, ema_length=100

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.845 | **FAIL** 0.700 |
| Max Drawdown (<=0.25) | PASS 0.151 | PASS 0.138 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **FAIL** 0.262 (310 trades) | **FAIL** 0.031 (308 trades) |
| Walk-forward (manual 4-way contiguous split; `check_walk_forward`'s vectorbt `RangeSplitter` API absent — manual fallback per repo convention) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter sensitivity (relative std <=0.5, 6-cell sweep) | PASS 0.487 (near ceiling) | PASS 0.309 |

## Decision: REJECT

Raw gross Sharpe already fails on both QQQ and SPY at the grid-optimal
config, and net-of-cost Sharpe collapses further (SPY 0.031, essentially
flat) given the high trade frequency (~308-310 round trips over 7.5 years) --
the tight SMA-of-high/low bands (vs a proper Donchian rolling max/min) break
too often relative to the edge they capture. The grid's 0/24 high-vol-regime
pass rate corroborates that this construction has no robust edge outside
calm markets. Not pursued to crypto given the equity-level failure.

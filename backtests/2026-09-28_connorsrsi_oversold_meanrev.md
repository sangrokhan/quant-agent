# ConnorsRSI (CRSI) Composite Oversold Mean-Reversion — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_connorsrsi_oversold_meanrev.py`
**Source:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/connorsrsi (StockCharts ChartSchool, read via browser_exec — web_extract's ddgs backend is search-only and cannot extract URL content)

## Hypothesis

ConnorsRSI (Larry Connors / Connors Research): a 3-component composite
oscillator averaging (1) RSI(3) of price, (2) RSI(2) of the up/down streak
length, and (3) PercentRank(100) of the 1-bar rate of change. Source
recommends CRSI < 10 (oversold, buy signal) / > 90 (overbought). This
repo has tested Connors' simpler RSI(2) and "Double Seven" strategies
before but never the actual 3-component ConnorsRSI composite — first full
implementation in this repo.

Tested: long entry when CRSI crosses below oversold_threshold within a
SMA(200) uptrend; exit when CRSI crosses back above exit_threshold (mean
reversion target) or a max_hold_days time-stop.

## Grid test summary (oversold_threshold∈{5,10,15} × exit_threshold∈{50,70} × max_hold_days∈{10,15}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 144, passed_cells: 28, **pass_fraction: 0.194** (highest of this cron trigger's iterations so far)
- by_asset_class: equity 22/72 (strongly outperforms); crypto 6/72
- by_vol_regime: low 18/48; mid 8/48; high 2/48 (edge concentrated in calm regimes, typical mean-reversion pattern)
- Best symbol-level configs: SPY oversold_threshold=15/exit_threshold=50/max_hold_days=10 (avg grid Sharpe 1.162); QQQ same params (avg 1.060); ETH/USDT oversold_threshold=10/exit_threshold=50 (avg 0.961)

## Single-config validation

| Symbol (config) | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| SPY (os=15/exit=50/hold=10) | 0.952 (FAIL, thr 1.0, very close) | 0.081 (PASS) | 0.404 (FAIL, thr 0.5) | 1.0 (PASS) | 0.858 (FAIL) |
| QQQ (os=15/exit=50/hold=10) | 0.899 (FAIL) | 0.095 (PASS) | 0.433 (FAIL) | 0.75 (PASS) | 0.436 (PASS) |
| ETH/USDT (os=10/exit=50/hold=10) | 0.891 (FAIL) | 0.041 (PASS) | 0.824 (PASS) | 1.0 (PASS) | 0.410 (PASS) |
| BTC/USDT (os=10/exit=50/hold=10) | 0.240 (FAIL, decisive) | 0.157 (PASS) | 0.196 (FAIL) | 0.75 (PASS) | 0.321 (PASS) |

## Decision: **REJECT**

Every symbol falls short of the 1.0 Sharpe threshold, but SPY/QQQ/ETH are
all close near-misses (0.89-0.95) with MDD comfortably passing across the
board and walk-forward robust — the strategy has real, honest, if
sub-threshold, edge. TC-survival fails on the equity legs specifically
because of a relatively high trade count (100-105 trades over 8yr) — the
mean-reversion entry fires often at oversold_threshold=15. A future
iteration could retest with a tighter oversold_threshold (e.g. 5-10 per
Connors' own more-conservative recommendation) to cut trade frequency and
transaction-cost drag while likely preserving or improving the per-trade
edge, which is the most promising rescue path for this near-miss family.
BTC/USDT is a decisive reject (Sharpe 0.24, TC-survival fails badly) and
should not be revisited without a different mechanism.

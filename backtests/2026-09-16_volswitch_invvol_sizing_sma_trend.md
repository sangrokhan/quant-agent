# 2026-09-16 Volatility Switch (VOLSWITCH) Inverse-Vol Continuous Sizing

## Hypothesis
Volatility Switch (VOLSWITCH), by Ron McEwan (Stocks & Commodities Feb
2013), per LazyBear's TradingView port visited this iteration
(https://www.tradingview.com/v/50YzpVDY/): estimates current volatility vs
historical, normalized to [0,1]. Source's own rule: VOLSWITCH<0.5 signals
decreasing volatility ("a sign of trend formation"), VOLSWITCH>0.5 signals
increasing/choppy volatility ("Use RSI to look for OB/OS levels" instead of
trend-following). The underlying construction is the rolling standard
deviation of a symmetric bar-to-bar price-change ratio (2*(Ct-Ct-1)/
(Ct+Ct-1)), min-max normalized to [0,1]. First VOLSWITCH-specific strategy
in this repo. Reframed as a CONTINUOUS SIZING dial — INVERTED (low
VOLSWITCH → high exposure, per the source's own "sign of trend formation"
guidance) inside an SMA(trend_window) uptrend gate with deadband, following
this repo's established inverse-volatility-conditioning pattern (cf.
Donchian Channel Width, `2026-09-15-040`).

Discovered via: `web_search` returned garbage/unrelated results for the
discovery query this iteration, so **fell back to `browser_exec`** per
RESEARCH_LOOP.md.

## Grid test (Step 6)
`run_grid_volswitch_sizing.py`: `sensitivity in [0.4,0.5,0.6]` x
`deadband in [0.20,0.30]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
(crypto), `vol_regime_splits=3`.

- total_cells: 72, passed_cells: 34, **pass_fraction: 0.472**
- by_asset_class: equity 18/36, crypto 16/36
- by_vol_regime: low 24/24, mid 6/24, high 4/24
- best_cell: QQQ, sensitivity=0.5/deadband=0.3, low-vol, Sharpe 2.631

## Single-config validation (Step 7)
QQQ passed cleanly at default-ish params. **BTC/USDT and ETH/USDT initially
failed MDD** (0.297/0.339 > 0.25 at leverage_cap=1.0) — leverage-cap
retune (0.6) rescued both. **SPY failed on Sharpe (0.735) and TC-survival
(0.28)**; a broad parameter sweep (trend_window, vs_period, sensitivity,
deadband) found no passing configuration — SPY is rejected for this
strategy, no rescue found.

| Symbol   | trend_window | vs_period | sensitivity | deadband | leverage_cap | Sharpe | MDD   | TC net Sharpe | Walk-forward | Param sens. |
|----------|-------------:|----------:|------------:|---------:|--------------:|-------:|------:|---------------:|-------------:|------------:|
| QQQ      | 40           | 14        | 0.5         | 0.30     | 1.0            | 1.287  | 0.125 | 0.911           | 1.00 (4/4)   | 0.062       |
| BTC/USDT | 40           | 14        | 0.24        | 0.30     | 0.6            | 1.282  | 0.198 | 1.073           | 1.00 (4/4)   | 0.087       |
| ETH/USDT | 40           | 14        | 0.24        | 0.30     | 0.6            | 1.393  | 0.222 | 1.266           | 1.00 (4/4)   | 0.051       |

All 5 validators pass on QQQ/BTC/ETH.

## Decision
**Accept (QQQ, BTC/USDT, ETH/USDT). Reject (SPY — no viable config found
across a wide parameter sweep).**

## Source
https://www.tradingview.com/v/50YzpVDY/ (LazyBear's VOLSWITCH port,
visited this iteration via browser_exec after web_search returned
garbage/unrelated results for the discovery query).

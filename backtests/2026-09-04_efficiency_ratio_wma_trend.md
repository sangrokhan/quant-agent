# Kaufman Efficiency Ratio (ER) + WMA Trend Filter — Backtest Report (2026-09-04)

## Hypothesis
Kaufman Efficiency Ratio (ER/KER): ratio of net closing-price change over
N periods to the sum of absolute bar-to-bar changes over the same N
periods -- range 0.0 (noisy) to 1.0 (perfectly efficient trend). Source
(quantifiedstrategies.com) formula is free; full coded rules are
membership-gated, but a Google SERP snippet from a CoinQuant strategy page
gave a concrete threshold rule: "Enter long when the Efficiency Ratio(10)
rises above 0.30". ER alone only measures trend STRENGTH, not direction,
so we add a WMA trend-direction filter: long entry when ER(er_period) >
er_threshold AND close > WMA(trend_window); exit when ER drops back below
threshold, close crosses below the WMA, or a max_hold_days time-stop.

Sources:
- https://www.google.com/search?q=%22Kaufman+Efficiency+Ratio%22+trading+strategy+rules+backtest
  (SERP snippets, including the CoinQuant threshold rule)
- https://www.quantifiedstrategies.com/efficiency-ratio/ (formula detail;
  full coded rules membership-gated)
(web_search failed for both original queries this iteration -- DDGS
"No results found" / RequestError -- fell back to browser_exec Google
search directly. Two follow-up links from the SERP, coinquant.ai and
luxalgo.com, both 404'd and were logged unhelpful.)

## Grid summary (Step 6)
`param_grid={er_threshold:[0.2,0.3,0.4], trend_window:[50,100]}`
(er_period=10 fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=10, **pass_fraction=0.139**
- by_asset_class: equity 10/36, crypto **0/36**
- by_vol_regime: low **10/24**, mid 0/24, high 0/24 (entirely low-vol-concentrated)
- best_cell: er_threshold=0.2, trend_window=50, QQQ, low-vol, Sharpe=2.20
- worst_cell: er_threshold=0.3, trend_window=50, SPY, mid-vol, Sharpe=-0.30

## Single-config validation (Step 7)
Config: er_threshold=0.2, trend_window=50, er_period=10 (grid-best cell
config). Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.931 (**fail**, near-miss) | 0.454 (**fail**) |
| Max drawdown (<=0.25) | 0.139 (pass) | 0.175 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.636 (pass) | 0.124 (**fail**) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 1.0, 4/4 splits positive (pass) | 1.0, 4/4 splits positive (pass) |
| Parameter sensitivity (er_threshold in {0.2,0.3,0.4}, rel std <=0.5) | 0.291 (pass) | 0.245 (pass) |
| num_trades | 159 | 166 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for QQQ** — full-sample Sharpe (0.931) narrowly misses the 1.0
threshold; all other validators pass, so this is a genuine near-miss
worth revisiting with a tighter er_threshold or shorter trend_window.
**Reject for SPY** — full-sample Sharpe (0.454) and net-of-cost Sharpe
(0.124) both fail decisively.
**Reject for crypto** — 0/36 grid cells pass.

Nothing accepted this iteration. QQQ near-miss (0.931 Sharpe, all other
4 validators passing cleanly with a perfect 4/4 walk-forward) is worth a
future revisit -- e.g. tightening er_threshold toward 0.15 or shortening
trend_window, since the grid-best-cell figure (2.20 on low-vol) suggests
there is real signal here that a slightly different config might convert
into a full pass.

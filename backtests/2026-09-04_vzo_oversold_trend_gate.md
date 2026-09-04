# Volume Zone Oscillator (VZO) Oversold-Recovery + Trend Gate — Backtest Report (2026-09-04)

## Hypothesis
Volume Zone Oscillator (VZO, Walid Khalil & David Steckler, 2009/2011):
VZO = 100*(VP/TV), VP = EMA of signed (OBV-style) volume, TV = EMA of raw
volume. Source (quantifiedstrategies.com) gives the free rule: combine
with an ADX(14) > 18 trend-strength filter and a 60-period EMA
trend-direction filter; in an uptrend, VZO crossing back above the -40%
oversold level is a buy signal. Implemented long-only with a
max_hold_days time-stop and exit on trend-filter breakdown.

Source: https://www.quantifiedstrategies.com/volume-zone-oscillator/
(web_search failed for both original queries this iteration -- DDGS
RequestError -- fell back to browser_exec Google search; two other SERP
links, Investopedia and trendsandbreakouts.com, 404'd / hit a bot-check
interstitial respectively and were logged unhelpful).

## Grid summary (Step 6)
`param_grid={adx_threshold:[15.0,18.0,22.0], max_hold_days:[15,20]}`
(vzo_period=14, oversold_level=-40.0, trend_window=60 fixed), symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=72, passed_cells=2, **pass_fraction=0.028** (very weak grid,
  a red flag before even running single-config validators)
- by_asset_class: equity 2/36, crypto **0/36**
- by_vol_regime: low 2/24, mid 0/24, high 0/24
- best_cell: adx_threshold=15.0, max_hold_days=20, SPY, low-vol, Sharpe=1.08
- worst_cell: adx_threshold=15.0, max_hold_days=15, QQQ, mid-vol, Sharpe=-1.50

## Single-config validation (Step 7)
Config: adx_threshold=15.0, max_hold_days=20 (grid-best cell config,
looser ADX threshold than the source's own 18 to generate more trades).
Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | -0.634 (**fail**, decisive, negative) | -0.109 (**fail**, negative) |
| Max drawdown (<=0.25) | 0.172 (pass) | 0.059 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | -0.677 (**fail**, decisive) | -0.172 (**fail**) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.25, 1/4 splits positive (**fail**) | 0.5, 2/4 splits positive (**fail**) |
| Parameter sensitivity (adx_threshold sweep, rel std <=0.5) | 0.133 (pass) | 0.852 (**fail**) |
| num_trades | 9 | 9 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for both QQQ and SPY, decisively.** Both have negative full-sample
Sharpe (the strategy loses money net of even zero costs), fail
TC-survival outright, and fail walk-forward. Only 9 entries occur over
the ~7.5-year sample at this config -- the ADX(14)>15 + EMA(60) trend
filter combined with the -40% oversold-recovery trigger is simply too
rare an event to generate a reliable edge at daily-bar resolution on
these two symbols; the grid-best-cell Sharpe (1.08 on SPY low-vol) came
from too small a sample of trades within that single tercile slice to be
meaningful.
**Reject for crypto** — 0/36 grid cells pass.

Nothing accepted this iteration. Given the extremely low trade count,
this indicator/filter combination is not worth revisiting at this
threshold configuration without either loosening the trend gate
substantially or moving to a higher-frequency timeframe where the
oversold-recovery event occurs often enough to build statistical
confidence.

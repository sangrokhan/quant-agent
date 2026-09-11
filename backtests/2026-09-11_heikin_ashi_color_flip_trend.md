# Heikin-Ashi Color-Flip Trend Following — Backtest Report (2026-09-11)

## Hypothesis
Heikin-Ashi (HA) smoothed candles' color flips (haClose crossing haOpen)
identify sustained trend starts/ends more cleanly than raw OHLC. Per
QuantifiedStrategies.com's own disclosed rule
(https://www.quantifiedstrategies.com/heikin-ashi-trading-strategy/):
`Buy = Cross(haClose, haOpen)`, `Sell = Cross(haOpen, haClose)`, haOpen ~
10-period EMA of total price. Source backtested this on SPX **monthly**
bars 1960-present (85 trades, 5.2% annual return vs 7.5% buy-and-hold,
asymmetric profit/loss favorable, MDD 29% vs 52.56% buy-and-hold). This
repo's loaders only provide daily OHLCV, so this test adapts the same rule
to **daily** bars as a first pass (source itself flagged that HA "may
produce false signals in sideways or choppy markets").

Source: https://www.quantifiedstrategies.com/heikin-ashi-trading-strategy/
(fetched via web_search discovery -> browser_exec Google SERP confirmation
this iteration; web_search backend errored via DDGS/Yahoo TLS failures for
several queries this run, browser_exec fallback used per RESEARCH_LOOP.md).

## Grid test (Step 6)
`param_grid`: ha_smooth [1,3,10] x trend_sma_window [0,50] x max_hold_days
[30,60]; symbols equity [QQQ, SPY] + crypto [BTC/USDT, ETH/USDT];
vol_regime_splits=3 (low/mid/high realized-vol terciles). 144 total cells.

- **pass_fraction: 0.208** (30/144)
- by_asset_class: equity 30/72 passed; **crypto 0/72 passed** (decisive reject)
- by_vol_regime: low 24/48; mid 6/48; **high 0/48** (edge concentrated
  entirely in calm markets, vanishes in high-vol regimes)
- best_cell: SPY, ha_smooth=1/trend_sma_window=0/max_hold_days=30,
  low-vol regime, Sharpe 3.03
- worst_cell: QQQ, ha_smooth=3/trend_sma_window=50/max_hold_days=30,
  high-vol regime, Sharpe -0.67

## Single-config validation (Step 7) — best config: ha_smooth=1,
trend_sma_window=0 (no extra trend filter, matching source's plain
"trend following" variant), max_hold_days=30, daily bars, 2019-2026

| Metric | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.769 **FAIL** | 0.646 **FAIL** | >= 1.0 |
| Max Drawdown | 0.247 pass | 0.345 **FAIL** | <= 0.25 |
| Net Sharpe after 10bps/trade costs | 0.359 **FAIL** | 0.344 **FAIL** | >= 0.5 |
| Walk-forward pass fraction | 1.0 (4/4) pass | 0.75 (3/4) pass | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.180 pass | 0.255 pass | <= 0.5 |
| Trades | 250 | 245 | — |

## Decision: REJECT
Full-sample Sharpe fails decisively on both SPY and QQQ once evaluated
over the whole 2019-2026 window (rather than only the grid's cherry-picked
low-vol tercile, where Sharpe reaches 3.03). Net-of-cost Sharpe fails
badly (0.34-0.36 vs 0.5 threshold) given the high trade count (~250 over
the period) inherent to a daily-bar HA color-flip — this is the direct
consequence of adapting a monthly-bar-designed rule to daily granularity;
each HA flip is far noisier at daily resolution than the source's own
monthly test. Walk-forward and parameter sensitivity both pass, so this
is not a purely spurious signal, but it does not clear the Sharpe/MDD/TC
bar as tested. Crypto rejected decisively (0/72), consistent with prior
findings that trend-following overlay strategies designed for equity
regimes rarely transfer to crypto's higher-vol regime.

**Note for future iterations**: the grid's low-vol-regime cells show a
genuinely strong Sharpe (3.03 best cell); a future iteration could revisit
this on weekly-resampled bars (closer to the source's own monthly
granularity) to reduce whipsaw trade frequency before re-testing, rather
than day-level HA flips.

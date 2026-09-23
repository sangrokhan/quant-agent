# 52-Week High Proximity Anchoring (Single-Asset Sizing Dial) — Backtest Report (2026-09-24)

## Hypothesis

George & Hwang (2004, Journal of Finance) 52-week-high anchoring effect:
stocks near their 52-week high exhibit systematic underreaction —
investors anchor to the old high as a psychological ceiling, and its
eventual breach triggers predictable continuation drift. Source
(https://blog.tradingstudio.finance/52-week-high-proximity-us-stocks/,
discovered via `web_search`, full text read via `browser_exec` since the
`web_extract` backend is search-only) uses a cross-sectional
`proximity_ratio = adjClose / MAX(high, 252d)` signal to rank a stock
universe (top-30 quarterly rebalance) — infeasible in this repo's
single-symbol architecture. This strategy adapts the same proximity_ratio
construction into a single-asset continuous-sizing dial: exposure scales
linearly with proximity_ratio above a `min_proximity` floor, up to
`leverage_cap` at proximity_ratio=1.0 (at the high). A `deadband` reduces
low-value rebalancing churn (established fix pattern from prior
continuous-sizing-dial strategies in this repo, e.g. Ultimate Oscillator
2026-09-13-079).

First "52-week high proximity" / anchoring-hypothesis strategy in this
repo (0 prior KB hits for "52 week high", "proximity ratio", "anchoring
hypothesis", George & Hwang).

## Strategy file

`strategies/2026-09-24_52wk_high_proximity_sizing.py`

## Grid test summary (Step 6)

144 cells: `min_proximity ∈ {0.80, 0.85, 0.90}` × `lookback_days ∈ {126,
252}` × `deadband ∈ {0.05, 0.1}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}`
× 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.424 (61/144) |
| equity pass | 34/72 |
| crypto pass | 27/72 |
| low-vol pass | 43/48 |
| mid-vol pass | 15/48 |
| high-vol pass | 3/48 |
| best cell | SPY low-vol, min_proximity=0.85/lookback=252/deadband=0.1, Sharpe 2.64 |
| worst cell | QQQ high-vol, min_proximity=0.9/lookback=126/deadband=0.05, Sharpe -0.68 |

Notably holds up across BOTH asset classes at 0.67 pass_fraction (2/3 vol
regimes) for several QQQ, BTC/USDT, and ETH/USDT configs — one of the
broader-transferring grids in this repo's recent history (crypto 27/72 vs
this cron trigger's other strategy's crypto 12/72).

## Single-config validation (Step 7)

| Validator | QQQ (min_prox=0.85, lb=252, db=0.1) | SPY (same) | BTC/USDT (min_prox=0.9, lb=252, db=0.05) | ETH/USDT (min_prox=0.9, lb=126, db=0.05) |
|---|---|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.099 | FAIL 0.977 | **PASS** 1.093 | FAIL 0.735 |
| Max Drawdown (<=0.25) | PASS 0.139 | PASS 0.143 | PASS 0.237 | FAIL 0.321 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 0.788 | PASS 0.722 | PASS 0.728 | PASS 0.518 |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) | PASS 1.0 (4/4) | PASS 0.75 (3/4) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.042 | PASS 0.030 | PASS 0.023 | PASS 0.143 |

QQQ: 5/5 pass. BTC/USDT: 5/5 pass (walk-forward exactly at the 0.75
threshold, one of 4 splits negative). SPY: 4/5 pass, Sharpe near-miss
(0.977 vs 1.0). ETH/USDT: 3/5 pass, decisive Sharpe and MDD fail.

## Decision

**Accept for QQQ and BTC/USDT.** Reject SPY (Sharpe near-miss, could be
revisited with parameter tweaks in a future iteration) and ETH/USDT
(decisive Sharpe + MDD fail). Strategy file and this report kept; log
entry records the QQQ+BTC/USDT accepted scope explicitly, with per-symbol
parameter configs (equity uses min_proximity=0.85/lookback=252/deadband=0.1;
crypto BTC/USDT uses min_proximity=0.9/lookback=252/deadband=0.05).

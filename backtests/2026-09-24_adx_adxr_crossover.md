# ADX/ADXR Crossover — Backtest Report (2026-09-24)

## Hypothesis

ADX crosses above its own smoothed sibling ADXR (`ADXR[t] = (ADX[t] + ADX[t-period]) / 2`)
signals trend acceleration → long entry, gated by `+DI > -DI` directional
confirmation. Exit on ADX crossing below ADXR, or a `max_hold_days` time-stop.

Source: Google AI-overview synthesis of TradingPedia / alphasquare.co.kr /
Linnsoft ADXR explainers (accessed via browser_exec Google SERP fallback —
`web_search` DDGS backend intermittently returned empty results this
iteration). Distinct from this repo's 6 prior ADXR entries: none tested this
specific two-line ADX-vs-ADXR crossover trigger (prior work used discrete
threshold-crossing, continuous-sizing dial, or a multiplicative
Commodity-Selection-Index combo).

## Strategy file

`strategies/2026-09-24_adx_adxr_crossover.py`

## Grid test summary (Step 6)

96→72 cells: `adx_period ∈ {10, 14, 20} × max_hold_days ∈ {20, 40}` ×
symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.417 (30/72) |
| equity pass | 16/36 |
| crypto pass | 14/36 |
| low-vol pass | 22/24 |
| mid-vol pass | 6/24 |
| high-vol pass | 2/24 |
| best cell | ETH/USDT mid-vol, adx_period=10/max_hold=40, Sharpe 2.56 |
| worst cell | SPY high-vol, adx_period=20/max_hold=20, Sharpe -1.31 |

Edge concentrated in low-vol regime, as usual for this repo's momentum-style
entries, but with meaningfully broader coverage (0.417) than most rejected
candidates this trigger.

## Single-config validation (Step 7)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | adx_period=14, max_hold=40 | 1.019 ✅ | 0.133 ✅ | 0.942 ✅ | 1.0 ✅ | 0.215 ✅ | **ACCEPT** |
| SPY | adx_period=10, max_hold=20 | 0.717 ❌ | 0.119 ✅ | 0.546 ✅ | 0.75 ✅ | 0.639 ❌ | REJECT |
| BTC/USDT | adx_period=10, max_hold=40 | 1.356 ✅ | 0.411 ❌ | 1.323 ✅ | 1.0 ✅ | 0.126 ✅ | REJECT (MDD) |
| ETH/USDT | adx_period=10, max_hold=20 | 1.391 ✅ | 0.332 ❌ | 1.364 ✅ | 1.0 ✅ | 0.277 ✅ | REJECT (MDD) |

QQQ: 44 trades, all 5 validators pass with healthy margins.

SPY: Sharpe and parameter-sensitivity both fail — the ADX/ADXR line-cross
signal is not stable enough on SPY across the parameter grid tested.

BTC/USDT and ETH/USDT: strong Sharpe, TC-survival, walk-forward and
parameter-sensitivity, but a *decisive* (not near-miss) MDD failure —
0.411 and 0.332 vs the 0.25 threshold. Flagged in the knowledge base as a
good candidate for a future leverage-cap-recalibration follow-up (this
repo's established rescue pattern, e.g. NVI 2026-09-14-131 →
2026-09-14-196).

## Decision

**Accepted for QQQ only.** Strategy file and this report kept as the live
QQQ config. SPY and crypto configs are documented rejections, not deleted,
per Step 8 guidance.

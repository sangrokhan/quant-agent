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

## Leverage-cap rescue follow-up (2026-09-24-019)

BTC/USDT and ETH/USDT both failed only MDD (decisive, not near-miss) at
`leverage_cap=1.0`. Since Sharpe is invariant to a uniform scalar exposure
multiplier (risk-free rate = 0 in these validators), a leverage_cap sweep
`{0.3, 0.4, 0.5, 0.6, 0.7}` was run to find the highest exposure that still
clears the MDD threshold:

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| BTC/USDT | adx_period=10, max_hold=40, **leverage_cap=0.5** | 1.356 ✅ | 0.224 ✅ | 1.283 ✅ | 1.0 ✅ | ~0 ✅ | **ACCEPT** |
| ETH/USDT | adx_period=10, max_hold=20, **leverage_cap=0.7** | 1.391 ✅ | 0.241 ✅ | 1.351 ✅ | 1.0 ✅ | ~0 ✅ | **ACCEPT** |

## Decision

**Accepted for QQQ (leverage_cap=1.0 default), BTC/USDT (leverage_cap=0.5),
and ETH/USDT (leverage_cap=0.7).** SPY remains rejected (Sharpe +
parameter-sensitivity fail). Strategy file's `leverage_cap` kwarg (default
1.0, backward-compatible) added specifically to support this rescue.

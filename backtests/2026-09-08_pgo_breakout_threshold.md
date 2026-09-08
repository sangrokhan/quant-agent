# Pretty Good Oscillator (PGO) Breakout Threshold — Backtest Report

**Date:** 2026-09-08 | **Strategy file:** `strategies/2026-09-08_pgo_breakout_threshold.py` | **Outcome: REJECTED (near-miss)**

## Hypothesis
Per pineify.app's PGO explainer (browser_exec fallback — web_extract failed,
DuckDuckGo search-only backend), Mark Johnson's Pretty Good Oscillator
PGO=(Close-SMA(N))/EMA(TrueRange,N) is an ATR-normalized distance-from-mean
breakout system. Source's own explicit rule: long entry when PGO crosses
above +3.0; exit when PGO reverts to the zero line. First PGO strategy in
this repo.

Source: https://pineify.app/pine-script/indicators/pgo

## Grid test (n=[21,55,89] x entry_threshold=[2.0,3.0], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- 72 cells total, 14 passed (pass_fraction 0.194)
- By asset class: equity 14/36, crypto 0/36 (decisive fail)
- By vol regime: low 12/24, mid 2/24, high 0/24
- Best cell: n=55/entry_threshold=2.0, QQQ low-vol, Sharpe 3.33
- Best per-symbol avg-across-regime configs: QQQ n=55/et=2.0 avg Sharpe 1.15; SPY n=89/et=2.0 avg Sharpe 1.07 (using a lower entry_threshold=2.0 than Johnson's default 3.0 -- 3.0 was consistently weaker in the grid on both tickers)

## Single-config validators (per-symbol tuned configs, exit_threshold=0.0, max_hold_days=60)

| Validator | QQQ (n=55, et=2.0) | SPY (n=89, et=2.0) | Threshold |
|---|---|---|---|
| Sharpe (full-sample) | 0.998 near-miss | 0.914 near-miss | >= 1.0 |
| Max Drawdown | 0.252 **FAIL** (barely) | 0.155 PASS | <= 0.25 |
| TC survival (10bps) | 0.963 PASS | 0.862 PASS | >= 0.5 |
| Walk-forward (4-split manual) | 0.75 PASS | 0.75 PASS | >= 0.75 |
| Parameter sensitivity | 0.354 PASS | 0.355 PASS | <= 0.5 |
| Trade count | 25 | 26 | n/a (informational, reasonable sample) |

Crypto context (n=55/et=2.0, full-sample, not the grid's crypto-tuned
config): BTC/USDT Sharpe 0.203, ETH/USDT Sharpe 0.238 — clear fail.

## Verdict
**REJECTED (near-miss).** Unlike several recent rejections with 2-3 trade
sample sizes, this one has a legitimate 25-26 trade sample on both QQQ and
SPY and clears TC-survival, walk-forward, and parameter sensitivity — but
full-sample Sharpe on both tickers falls just short of the 1.0 threshold
(0.998, 0.914), and QQQ's max drawdown barely breaches the 0.25 cap
(0.252). A tightened threshold (entry_threshold=2.0 rather than Johnson's
own recommended 3.0) was needed just to reach this near-miss level — using
Johnson's literal +3.0 threshold scored notably lower in the grid (QQQ avg
Sharpe 1.117 at et=3.0 vs 1.152 at et=2.0, but single-config full-sample
results at et=3.0 were weaker still, not run in detail here since et=2.0
was already the stronger grid candidate). Crypto rejected decisively.
Worth flagging as a genuine near-miss for a future loop to revisit with a
tighter MDD-control tweak (e.g. an ATR trailing stop) rather than a
fundamentally broken idea.

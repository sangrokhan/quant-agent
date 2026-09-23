# Break of Structure (BOS) Trend-Continuation Pullback-Retest — Backtest Report (2026-09-24)

## Hypothesis

Per fluxcharts.com's "Break of Structure (BOS) Explained", Daily Price
Action's "SMC Market Structure: BoS And CHoCH Made Simple", and
Evest/SabioTrade/Pineify's BOS guides (surfaced via a Google AI-overview
synthesis after `web_search` returned no results; `browser_exec` fallback
used): a bullish Break of Structure (BOS) occurs during an ALREADY
established uptrend (Higher-High/Higher-Low sequence) when price
candle-body closes above the most recent Higher High, confirming trend
CONTINUATION -- the opposite economic thesis from this cron trigger's
earlier Change of Character strategy (2026-09-24-039, reversal signal
during a downtrend). Sources' own recommended sequencing is to wait for a
pullback/retest of the just-broken prior high (which becomes new support)
before entering, rather than chasing the breakout bar. First
Break-of-Structure strategy in this repo (0 prior KB hits).

## Strategy file

`strategies/2026-09-24_bos_trend_continuation_retest.py`

## Grid test summary (Step 6)

96 cells: `swing_window ∈ {3, 5}` × `retest_window ∈ {5, 10}` ×
`max_hold_days ∈ {20, 30}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3
vol-regime terciles, 2019–2026.

| Metric | Value |
|---|---|
| pass_fraction | 0.417 (40/96) |
| equity pass | 22/48 |
| crypto pass | 18/48 |
| low-vol pass | 20/32 |
| mid-vol pass | 14/32 |
| high-vol pass | 6/32 |
| best cell | QQQ low-vol, swing_window=5/retest_window=5/max_hold=20, Sharpe 2.55 |
| worst cell | SPY high-vol, swing_window=5/retest_window=5/max_hold=20, Sharpe -0.98 |

**BTC/USDT at swing_window=3/retest_window=5 or 10/max_hold=30 achieved a
PERFECT 3/3 vol-regime pass** — the strongest single grid configuration
found across all iterations this cron trigger.

## Single-config validation (Step 7)

| Validator | QQQ (sw=3, rw=5, mh=20) | SPY (sw=5, rw=5, mh=20) | BTC/USDT (sw=3, rw=5, mh=30) |
|---|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.404 | FAIL 0.814 | **PASS** 1.292 |
| Max Drawdown (<=0.25) | PASS 0.108 | PASS 0.090 | FAIL 0.280 |
| TC Survival (>=0.5 net Sharpe, 10bps/trade) | PASS 1.346 | PASS 0.732 | PASS 1.278 |
| Walk-Forward (>=0.75 pass fraction, 4 splits) | PASS 1.0 (4/4) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter Sensitivity (<=0.5 relative std) | PASS 0.341 | PASS 0.029 | PASS 0.078 |

QQQ: 5/5 pass, strong margins across the board. SPY: 4/5 pass, Sharpe
near-miss (0.814). BTC/USDT: 4/5 pass, MDD near-miss (0.280 vs 0.25
threshold) despite an excellent grid showing (perfect 3/3 vol-regime
pass) and a strong Sharpe (1.292) — a max_hold_days sweep (15/20/25) did
not bring MDD below the 0.25 threshold (stayed at 0.267-0.280), so this is
a stubborn near-miss rather than a quick parameter fix.

## Decision

**Accept for QQQ only.** SPY and BTC/USDT are both genuine near-misses
(one validator each, not decisive failures) worth flagging for a future
iteration's rescue attempt (e.g. BTC/USDT with a tighter stop-based exit
or a leverage-cap recalibration to address the MDD near-miss specifically,
following this repo's established rescue pattern). Strategy file and this
report kept; log entry records QQQ-only accepted scope plus both
near-misses explicitly for future revisit.

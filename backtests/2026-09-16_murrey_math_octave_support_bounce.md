# Backtest report: Murrey Math Octave Support Bounce (2026-09-16)

**Strategy file:** `strategies/2026-09-16_murrey_math_octave_support_bounce.py`
**KB entry:** `2026-09-16-180` (rejected)

## Hypothesis

Per Murrey Math Lines theory (T. Henning Murrey), a rolling `lookback_n`-bar
window is divided into 8 equal octaves: `0/8` = rolling low ("ultimate
support"), `8/8` = rolling high ("ultimate resistance"), `4/8` = midline.
Long entry when a bar's intraday low touches/breaches `0/8` and the close
reclaims back above it (support-hold reversal). Exit at the `4/8` midline
(take-profit), a stop beyond `0/8 - overshoot_buffer_mult*increment`, or a
`max_hold_days` time-stop.

**Source:** Google AI-overview synthesis of Murrey Math Lines entry/exit
rules (RoboForex, Scribd, LuxAlgo, EBC Financial Group, Slideshare), read
via `browser_exec` Google SERP (`web_search` DDGS backend failed both test
queries this iteration with a TLS connection error — immediate fallback per
RESEARCH_LOOP.md).

First Murrey Math strategy in this knowledge base (zero prior KB matches
for "Murrey Math" before this iteration).

## Grid test (Step 6)

`GridSpec(param_grid={"lookback_n": [32,64,96], "overshoot_buffer_mult":
[0.25,0.5,1.0], "max_hold_days": [15,20]}, symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` — 216 cells,
2018-01-01 to 2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 0/216 = 0.0 |
| by_asset_class | equity 0/108, crypto 0/108 |
| by_vol_regime | low 0/72, mid 0/72, high 0/72 |
| best cell | QQQ, lookback_n=32/overshoot_buffer_mult=0.25/max_hold_days=15, high-vol regime, Sharpe **0.992** |
| worst cell | ETH/USDT, lookback_n=64/overshoot_buffer_mult=0.25/max_hold_days=20, mid-vol regime, Sharpe -1.219 |

No cell in the grid cleared Sharpe≥1.0 AND MDD≤0.25 simultaneously. Failure
is uniform across asset classes and vol regimes — not concentrated in one
slice, ruling out a narrower-but-honest acceptance.

## Single-config validators (default params, full-sample QQQ)

`lookback_n=64, overshoot_buffer_mult=0.5, max_hold_days=20`

| validator | passed | value | threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | 0.381 | 1.0 |
| max_drawdown | ✅ | 0.171 | 0.25 |

Given the grid's decisive 0/216 pass fraction, walk-forward and parameter
sensitivity were not run separately (would not change the accept/reject
call) — this is scoped to `suggested_workload=max` but the grid result
already answers the accept/reject question decisively.

## Decision

**Rejected.** No parameter/symbol/vol-regime combination clears both the
Sharpe and MDD thresholds simultaneously. Best cell (QQQ high-vol,
Sharpe 0.992) is a genuine near-miss worth a future finer sweep, but the
strategy as specified does not meet acceptance criteria.

## Implementation note for future loops

The first entry-signal formulation (`prev_close < prev_level_0`, i.e. a
strict prior-bar close below the rolling-window-derived support line)
produced **zero trades** across all symbols/params, because `level_0` is
itself the rolling-window minimum low — a close below it on a *prior* bar
is nearly impossible by construction. Corrected to same-bar
`low <= level_0 AND close > level_0`. Worth remembering for any future
pivot/rolling-min-max-derived support/resistance strategy in this repo.

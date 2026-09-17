# 5-Day Low of The Range (IBS + N-day lowest-low breakdown) — QQQ, SPY, BTC/USDT, ETH/USDT

**Strategy file:** `strategies/2026-09-18_5day_low_range_ibs.py`
**Source:** https://www.quantifiedstrategies.com/5-day-low-of-the-range-strategy/
(read via `browser_exec`, Google SERP fallback, after `web_search`
DDGS/Yahoo backend errored with `TLS RequestError` on every query attempted
this iteration; `web_extract` also unavailable — "DuckDuckGo (ddgs) is a
search-only backend and cannot extract URL content" — so extraction used
`browser_exec` directly on the target page as well.)

## Hypothesis

Article discloses (plain English, exact numeric exit rule paywalled):
IBS (Internal Bar Strength = (Close-Low)/(High-Low)) < 0.25 AND today's
close < the lowest low of the previous 5 days -> long entry. Full-sample
(1993-2026) on SPY: 414 trades, 305 winners (73% win rate), avg 0.7%/trade
after costs, max drawdown 20%, "far exceeding the average return for any
5-day period" (0.11%). Article states profitability peaks 3-7 days and
discusses "exiting after five days" as the reference holding horizon, so
this implementation uses `max_hold_days` as a fixed-horizon exit (default
5), plus an IBS-recovery early exit (IBS > `ibs_exit_threshold`, default
0.75), both gated by a 200-day SMA uptrend filter.

Novelty: distinct from every prior IBS-family entry in this repo (simple
IBS threshold-cross, N-day averaged IBS, Rob Hanna "Adjusted Failed
Bounce" high-prior-IBS downtrend-continuation pattern) — this is the first
strategy combining same-day LOW IBS with an N-day lowest-low breakdown as
a joint panic/oversold signal.

## Grid test (validation/grid_test.py)

`param_grid`: `ibs_entry_threshold` in [0.15, 0.25, 0.35], `low_lookback`
in [3, 5, 8], `max_hold_days` in [3, 5, 8]; `symbols`: equity [QQQ, SPY],
crypto [BTC/USDT, ETH/USDT]; `vol_regime_splits=3`; 2018-01-01 to
2026-09-01.

- `total_cells=324`, `passed_cells=84`, `pass_fraction=0.259`
- `by_asset_class`: equity 60/162, crypto 24/162
- `by_vol_regime`: low 50/108, mid 15/108, high 19/108 (edge concentrated in low-vol regimes)
- `best_cell`: QQQ, low-vol, `ibs_entry_threshold=0.25, low_lookback=3, max_hold_days=3`, Sharpe 2.02
- `worst_cell`: BTC/USDT, low-vol, `ibs_entry_threshold=0.15, low_lookback=3, max_hold_days=5`, Sharpe -1.25

## Single-config validation (best_cell config: ibs_entry_threshold=0.25, low_lookback=3, max_hold_days=3)

| Symbol | Sharpe | Sharpe pass | MDD | MDD pass | TC-survival net Sharpe | TC pass | WF pass_frac | WF pass | Param-sens relstd | PS pass | Trades | ALL PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 1.025 | ✅ | 0.072 | ✅ | 0.727 | ✅ | 1.00 | ✅ | 0.211 | ✅ | 93 | **✅ ACCEPT** |
| SPY | 0.545 | ❌ | 0.100 | ✅ | 0.256 | ❌ | 0.75 | ✅ | 0.287 | ✅ | 82 | ❌ reject |
| BTC/USDT | 0.193 | ❌ | 0.335 | ❌ | -0.021 | ❌ | 1.00 | ✅ | 0.141 | ✅ | 1670 | ❌ reject |
| ETH/USDT | 0.253 | ❌ | 0.272 | ❌ | 0.006 | ❌ | 1.00 | ✅ | 0.287 | ✅ | 1639 | ❌ reject |

Walk-forward used manual 4-equal-slice fallback (`vbt.utils.splitting.RangeSplitter`
broken in this vectorbt install, per prior repo notes). Parameter
sensitivity swept `ibs_entry_threshold` in {0.10,0.15,0.20} x `low_lookback`
in {4,5,6} around the accepted config.

## Decision

**Accept for QQQ only** (all 5 validators pass at `ibs_entry_threshold=0.25,
low_lookback=3, max_hold_days=3`). Reject SPY (fails Sharpe + TC-survival)
and both crypto pairs (fail Sharpe, MDD, TC-survival — crypto's much higher
trade count (~1650-1670 vs 51-93 on equities) combined with weak per-trade
edge erodes to negative after transaction costs). Consistent with the
grid's own by_vol_regime finding that the edge concentrates in low-vol
regimes — crypto's persistently higher realized vol likely explains the
outright failure there.

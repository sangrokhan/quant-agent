# Backtest Report: Realized-Volatility Ratio Compression + Breakout

**Date:** 2026-09-16 (iteration 6, cron trigger 2026-09-15 ~15:00 KST)
**Strategy file:** `strategies/2026-09-16_rv_ratio_compression_breakout.py`

## Hypothesis

Per a Google AI-overview summary (FlashAlpha/LuxAlgo cited) of trading
volatility-risk-premium-style compression/expansion cycles WITHOUT
options-implied-vol data: compute `RV_ratio = RV_short(10d) /
RV_long(90d)`. `RV_ratio < 0.70` (source's own threshold) identifies a
"quiet/compressed" regime that historically precedes expansion. This
implementation adds the source's implied "confirm the expansion has
actually started" rule via a `breakout_window`-day new-high confirmation:
long when RV_ratio is below `compression_threshold` AND price makes a new
N-day high; exit when RV_ratio reverts above `exit_threshold` (vol
normalized back to baseline) or a `max_hold_days` time-stop. Distinct from
this repo's 4 prior "volatility compression" entries (all single-window
vol-percentile-rank constructions) since this uses a RATIO of two
different-timescale realized-vol measures as the regime signal, closer in
spirit to a VIX-term-structure trade.

Source read via `browser_exec` fallback after `web_search`'s DDGS backend
continued failing with the same Yahoo/TLS RequestError seen every
iteration this trigger.

## Grid test summary (Step 6)

`param_grid={compression_threshold: [0.60,0.70,0.80], breakout_window:
[10,20,30]}`, `symbols={equity: [QQQ,SPY], crypto: [BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`.

- total_cells: 108, passed_cells: 31, **pass_fraction: 0.287**
- by_asset_class: equity 21/54, crypto 10/54 (unusually high crypto grid
  pass count for this repo)
- by_vol_regime: low 27/36, mid 3/36, high 1/36
- best_cell: equity/SPY/low-vol, sharpe 2.90 (compression_threshold=0.7,
  breakout_window=30)
- worst_cell: equity/SPY/mid-vol, sharpe -1.06 (same param combo)

Best balanced full-grid config: `compression_threshold=0.6,
breakout_window=30` (equity 3/6, crypto 2/6 — highest combined pass count).

## Single-config validator results (Step 7)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Overall |
|---|---|---|---|---|---|---|
| QQQ | 1.389 (pass) | 0.077 (pass) | 1.312 (pass) | 1.00 (pass) | 0.172 rel-std (pass) | **ACCEPT** |
| SPY | 0.527 (fail) | 0.139 (pass) | 0.420 (fail) | 0.75 (pass) | 0.175 rel-std (pass) | REJECT |
| BTC/USDT | 0.888 (fail) | 0.429 (fail) | 0.862 (pass) | 0.50 (fail) | 0.149 rel-std (pass) | REJECT |
| ETH/USDT | 0.377 (fail) | 0.298 (fail) | 0.362 (fail) | 0.75 (pass) | 0.380 rel-std (pass) | REJECT |

## Decision

**Accept QQQ only.** QQQ clears all 5 validators comfortably (Sharpe 1.39,
very low MDD 7.7%, strong TC-survival, perfect walk-forward). SPY is a
Sharpe/TC near-miss-but-decisive fail, and both crypto symbols fail
multiple validators (BTC/USDT additionally fails walk-forward — only 2/4
splits positive). This is a QQQ-specific edge, not a broad multi-asset
mechanism; flagged as scope-limited per this repo's convention for
partial accepts. Strategy file and this report kept as the record of a
QQQ-only accepted strategy.

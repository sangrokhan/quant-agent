# VROC-Confirmed Donchian Breakout — REJECTED

**Strategy file:** `strategies/2026-09-12_vroc_donchian_breakout_confirm.py`
**Source:** https://blog.ueex.com/volume-rate-of-change-vroc/ (UEEx blog,
via browser_exec after web_search DDGS backend returned no useful results
for the initial query this iteration)

## Hypothesis

Per the source's disclosed rule ("a VROC reading above 200% is considered
strong breakout validation... wait for VROC to exceed the 200% threshold
before treating a breakout as confirmed"), a Donchian-channel price
breakout (close > prior N-day rolling high) confirmed by same-bar
Volume-Rate-of-Change >= threshold (100%/200%/300% tested) should filter
out low-conviction breakouts and improve on an unfiltered Donchian
breakout.

## Grid test summary (Step 6)

- Grid: `channel_window` in [15, 20, 30] x `vroc_threshold` in [100, 200,
  300]; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto);
  vol_regime_splits=3. 108 total cells.
- **pass_fraction: 0.028 (3/108)** — very weak
- by_asset_class: equity 3/54; **crypto 0/54 (decisive fail)**
- by_vol_regime: low 3/36; **mid 0/36, high 0/36 (decisive fail)**
- best_cell: channel_window=15, vroc_threshold=100, QQQ, low-vol, Sharpe 1.459

## Single-config check — full sample 2019-2026 (Sharpe only, given grid result already decisive)

| channel_window | vroc_threshold | QQQ Sharpe | SPY Sharpe |
|---|---|---|---|
| 15 | 100 | 0.881 | 0.405 |
| 15 | 200 | inf (near-zero trades) | -0.148 |
| 15 | 300 | inf (near-zero trades) | 0.094 |
| 30 | 100 | 0.881 | 0.633 |
| 30 | 200 | inf (near-zero trades) | 0.231 |
| 30 | 300 | inf (near-zero trades) | 0.094 |

The "inf" Sharpe readings at higher VROC thresholds are an artifact of the
filter becoming so restrictive that almost no trades fire (near-zero
variance, not genuine outperformance) — not evidence of a real edge. Even
the best plausible configuration (channel_window=15/30, vroc_threshold=100,
QQQ) tops out at Sharpe 0.881, below the 1.0 threshold, and SPY never
exceeds 0.633 across any tested combination.

## Decision: REJECTED (no single-config validation needed — grid result decisive)

The VROC>=200% confirmation threshold as literally specified by the source
makes the strategy trade too rarely to generate a reliable edge (many
cells show near-zero trade counts inflating Sharpe artificially), while a
looser 100% threshold trades more often but tops out at Sharpe <=0.881 on
both symbols, below this repo's 1.0 threshold. Crypto is decisively
rejected across all 54 cells. Per RESEARCH_LOOP.md Step 7 guidance, when
the grid result is this decisively negative, a further single-config
validator run is not warranted. A future iteration could explore VROC as a
softer position-sizing multiplier rather than a hard binary gate, or pair
it with a different (non-Donchian) breakout definition, but this direct
implementation of the source's own literal rule does not clear the bar.

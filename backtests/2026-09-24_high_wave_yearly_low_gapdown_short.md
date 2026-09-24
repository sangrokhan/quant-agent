# Backtest report: Bulkowski High Wave (yearly-low + gap-down + below-50SMA short)

**Strategy file:** `strategies/2026-09-24_high_wave_yearly_low_gapdown_short.py`
**Hypothesis source:** https://thepatternsite.com/HighWave.html (Thomas Bulkowski, browser_exec fallback — web_search's DDGS backend cannot usefully extract this domain)

## Hypothesis

High Wave candle (tall upper+lower shadows, small non-doji body) is
theoretically an indecision signal, and the source's own testing confirms
near-random 51% reversal (rank 67/103). The source's own disclosed single
strongest number across all four bull/bear x up/down combinations is a
downward move (-3.38% avg, bear market, down breakout). The source's own
"Three Trading Tidbits" disclose three refinements: yearly-low proximity,
opening-gap confirmation, and breakouts below the 50-day SMA. This
strategy shorts on the disclosed strongest-performing combination: a High
Wave candle near the yearly low, confirmed the next bar by a gap down that
closes below SMA(50).

## Grid test summary (Step 6)

`param_grid`: shadow_min_pct ∈ {0.25,0.3,0.4}, yearly_low_third ∈
{0.2,0.33}, target_atr_mult ∈ {1.5,2.0,3.0}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to
2026-09-01.

- **total_cells:** 216
- **passed_cells:** 0
- **pass_fraction:** 0.0
- **by_asset_class:** equity 0/108, crypto 0/108
- **by_vol_regime:** low 0/72, mid 0/72, high 0/72
- **best_cell:** shadow_min_pct=0.4, yearly_low_third=0.2, target_atr_mult=1.5, QQQ high-vol, Sharpe=0.575 (well below min_sharpe=1.0 threshold)
- **worst_cell:** SPY high-vol, Sharpe=-1.634
- **186/216 cells** ("empty/no-trade slice") — the compounding restriction of yearly-low proximity + gap-down confirmation (single-bar window) + below-50-SMA is very tight, leaving only 30 cells with any trades at all.

## Decision (Step 8): REJECT

Decisive grid failure — 0/216 pass_fraction, and unlike the prior two
rejections this cron trigger (Tweezers Bottom, Last Engulfing Bottom),
even the single best cell was far from the threshold (0.575 vs 1.0
required), with the vast majority of cells (186/216, 86%) producing zero
trades. This confirms the source's own framing that the raw pattern is
near-random (51%) — stacking three independent refinement filters produced
too sparse a signal to establish an edge in any asset class or vol regime.
No single-config validator suite (Step 7) run given the decisive grid
result.

Strategy/report files are kept in the repo as a record of a rejected
attempt (not a live strategy).

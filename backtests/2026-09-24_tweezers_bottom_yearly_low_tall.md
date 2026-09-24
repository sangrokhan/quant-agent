# Backtest report: Bulkowski Tweezers Bottom (yearly-low + tall-candle filter)

**Strategy file:** `strategies/2026-09-24_tweezers_bottom_yearly_low_tall.py`
**Hypothesis source:** https://thepatternsite.com/TweezersBottom.html (Thomas Bulkowski, browser_exec fallback — web_search's DDGS backend cannot usefully extract this domain)

## Hypothesis

Raw Tweezers Bottom (two candles sharing the same low, downtrend context) is
disclosed by the source as near-random: tested bearish continuation 52% of
the time, overall rank 44/103. The source's own "Three Trading Tidbits"
(book p.832/834) disclose that patterns occurring within a third of the
yearly low, with at least one tall candle, are the best-performing subset.
This strategy trades only that source-disclosed refined subset, entering
long on a close above the top of the tweezers pattern, with a Measure Rule
target / shared-low stop / time-stop exit.

## Grid test summary (Step 6)

`param_grid`: trend_window ∈ {15,20,30}, yearly_low_third ∈ {0.2,0.33},
max_hold_days ∈ {10,20}; symbols: equity {QQQ, SPY}, crypto {BTC/USDT,
ETH/USDT}; vol_regime_splits=3 (low/mid/high terciles); period
2019-01-01 to 2026-09-01.

- **total_cells:** 144
- **passed_cells:** 0
- **pass_fraction:** 0.0
- **by_asset_class:** equity 0/72, crypto 0/72
- **by_vol_regime:** low 0/48, mid 0/48, high 0/48
- **best_cell:** trend_window=15, yearly_low_third=0.33, max_hold_days=10, QQQ, mid-vol, Sharpe=0.872 (below min_sharpe=1.0 threshold)
- **worst_cell:** SPY high-vol, Sharpe=-1.343
- **42/144 cells** returned "empty/no-trade slice" (sparse signal in some vol-regime/symbol slices, consistent with the source's own disclosed near-random raw pattern plus an additional two-condition refinement filter further thinning an already infrequent 2-candle setup)
- Of the 102 cells that did produce trades, the maximum observed Sharpe across the entire grid was 0.872 — never crossing the 1.0 pass bar in any parameter/asset/vol-regime combination.

## Decision (Step 8): REJECT

Decisive grid failure — 0/144 pass_fraction, with the single best cell
still 13% below the Sharpe threshold and no asset class or vol regime
showing a viable pocket. Given the source's own explicit disclosure that
the raw pattern is "near random" (52% bearish continuation, rank 44/103),
this result is unsurprising: the yearly-low + tall-candle refinement
narrows an already weak, sparse setup further without adding enough edge
to clear the bar. No single-config validator suite (Step 7) run given the
decisive grid-level rejection — consistent with prior iterations this
cron trigger (e.g. Takuri Line, 2026-09-24-117) that skip Step 7 when the
grid result is unambiguous.

Strategy/report files are kept in the repo as a record of a rejected
attempt (not a live strategy).

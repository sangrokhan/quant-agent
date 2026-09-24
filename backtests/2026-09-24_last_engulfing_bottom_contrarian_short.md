# Backtest report: Bulkowski Last Engulfing Bottom (contrarian short, uptrend-retracement + yearly-low filter)

**Strategy file:** `strategies/2026-09-24_last_engulfing_bottom_contrarian_short.py`
**Hypothesis source:** https://thepatternsite.com/LastEngulfBottom.html (Thomas Bulkowski, browser_exec fallback — web_search's DDGS backend cannot usefully extract this domain)

## Hypothesis

Last Engulfing Bottom (white candle followed by a body-engulfing black
candle) is theoretically a bullish reversal, but the source's own testing
shows it acts as a bearish CONTINUATION pattern 65% of the time (rank
48/103 overall). The source's own "Three Trading Tidbits" disclose two
best-performing refinements: proximity to the yearly low, and trading it
as part of a downward retracement of a larger uptrend (rather than a raw
primary downtrend). This strategy trades the disclosed empirical reality
(contrarian SHORT on confirmed breakdown below the pattern low) within
both source-disclosed filters, with an ATR-based stop/target exit.

## Grid test summary (Step 6)

`param_grid`: uptrend_window ∈ {50,100,150}, yearly_low_third ∈
{0.2,0.33}, target_atr_mult ∈ {1.5,2.0,3.0}; symbols: equity {QQQ, SPY},
crypto {BTC/USDT, ETH/USDT}; vol_regime_splits=3; period 2019-01-01 to
2026-09-01.

- **total_cells:** 216
- **passed_cells:** 0
- **pass_fraction:** 0.0
- **by_asset_class:** equity 0/108, crypto 0/108
- **by_vol_regime:** low 0/72, mid 0/72, high 0/72
- **best_cell:** uptrend_window=50, yearly_low_third=0.2, target_atr_mult=1.5, BTC/USDT low-vol, Sharpe=0.970 (still below min_sharpe=1.0 pass threshold)
- **worst_cell:** QQQ mid-vol, Sharpe=-1.303
- **152/216 cells** ("empty/no-trade slice") — the combination of uptrend-retracement context + engulfing-body condition + yearly-low proximity filter is highly restrictive, leaving very few tradeable setups per vol-regime/symbol slice (consistent with the source's own "frequency rank 13/103" being for the RAW unfiltered pattern; adding two independent numeric filters sharply thins the sample).
- Of the 64 cells that did produce trades, the maximum Sharpe observed across the entire grid was 0.970 — never crossing the 1.0 pass bar.

## Decision (Step 8): REJECT

Decisive grid failure — 0/216 pass_fraction. The single best cell (crypto,
low-vol) came close (Sharpe 0.970) but still missed the threshold, and no
asset class or vol regime showed a consistently viable pocket; the
majority of cells (152/216, 70%) were empty due to the compounding
restrictiveness of the uptrend-retracement + yearly-low + engulfing-body
filter stack. No single-config validator suite (Step 7) run given the
decisive grid-level rejection, consistent with this cron trigger's
established practice of skipping Step 7 on unambiguous grid failures.

Strategy/report files are kept in the repo as a record of a rejected
attempt (not a live strategy).

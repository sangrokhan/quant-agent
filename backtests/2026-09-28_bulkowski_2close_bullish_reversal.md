# Bulkowski Bullish 2-Close Reversal — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_bulkowski_2close_bullish_reversal.py`
**Source:** https://thepatternsite.com/2Closebull.html (Thomas Bulkowski, read via browser_exec — web_extract's ddgs backend is search-only and cannot extract URL content)

## Hypothesis

Bulkowski's Bullish 2-Close Reversal: a 3-bar pattern (bar2 makes a lower
low + lower close than bar1; bar3 makes a lower low than bar2 but closes
above BOTH bar1 and bar2's closes). Source's own tested entry/exit rule:
buy-stop above pattern high, stop-loss below pattern low, target = 2x
pattern height above pattern high. Source's own conclusion is an explicit
negative prior ("poor performer... look elsewhere... flops in ETFs and
crypto") — this repo tests the concrete numeric rule anyway as an
independent falsification/confirmation check, following the same pattern
as the Bollinger Band squeeze test (2026-09-03-011) and Fibonacci
retracement test (2026-09-03-022).

First "2-Close" pattern tested in this repo (0 prior hits).

## Grid test summary (target_height_mult∈{1.0,2.0,3.0} × max_hold_days∈{15,25}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 72, passed_cells: 16, **pass_fraction: 0.222** (best of this cron trigger so far, tied with ConnorsRSI)
- by_asset_class: equity 16/36 (excellent); crypto 0/36 (decisive fail, consistent with source's own "flops in crypto" finding)
- by_vol_regime: low 12/24; mid 4/24; high 0/24 (calm-regime-only edge, typical reversal-pattern behavior)
- Best symbol configs: SPY target_height_mult=2.0 (avg grid Sharpe 0.936, 2/3 regime slices pass); QQQ target_height_mult=2.0/max_hold_days=25 (avg grid Sharpe 1.170, 1/3 regime slices pass)

## Single-config validation

| Symbol (config) | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ (target_height_mult=2.0, max_hold_days=25) | 0.732 (FAIL, thr 1.0) | 0.045 (PASS) | 0.648 (PASS) | 1.0 (PASS) | 0.174 (PASS, very stable) |
| SPY (target_height_mult=2.0, max_hold_days=15) | 0.764 (FAIL, thr 1.0) | 0.050 (PASS) | 0.640 (PASS) | 0.75 (PASS) | 0.057 (PASS, extremely stable) |

## Decision: **REJECT**

Both symbols fail only the Sharpe threshold (0.73, 0.76) while every
other validator passes comfortably, and parameter sensitivity is
exceptionally low (0.06-0.17 relative std) — this is a stable, low-noise,
if modest, edge, exactly matching the source's own characterization of
the pattern as a marginal-but-real outperformer in uptrends. This
confirms the source's own honest negative-to-neutral prior rather than
falsifying it: the pattern shows genuine (if too-modest) signal in
equities and a decisive crypto failure exactly as the source predicted.
Given the very low trade count (12-14 trades over 8yr), a future
iteration could try relaxing the trend filter or widening the symbol
universe (more equity tickers) to increase trade frequency and see if the
per-trade edge compounds to a passing Sharpe with more observations,
though the underlying edge itself appears capped by the source's own
findings.

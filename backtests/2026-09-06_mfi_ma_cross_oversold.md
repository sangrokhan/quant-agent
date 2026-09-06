# Money Flow Index (MFI) MA-Cross-From-Oversold Reversal

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_mfi_ma_cross_oversold.py`
**KB id:** 2026-09-06-129

## Hypothesis

Per TradingView's "Basic Money Flow Strategy" (SERP snippet): long entry
when MFI crosses above its own short moving average after coming from an
oversold (<20) reading; exit on the reverse cross or a time-stop. MFI is a
volume-weighted RSI variant (uses typical-price * volume as "money flow"),
a genuinely different indicator family from the plain-price RSI already
tested extensively in this repo.

**Source:** Google SERP snippet of TradingView's MFI strategies page
(web_search errored this iteration; browser_exec used for the search).

## Grid test (mfi_window=[10,14,21] x ma_window=[6,9,14], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026)

- **2/108 cells passed** (equity 2/54, crypto 0/54) — decisively weak
- Best avg-config: mfi_window=14, ma_window=14, QQQ avg Sharpe only 0.557 across regimes
- QQQ full-sample single-config Sharpe at best avg-config: **0.242** — far below the 1.0 threshold

## Decision: **REJECT**

Decisive rejection at the grid stage (2/108 cells, 1.9% pass fraction) with
the best average-config full-sample Sharpe (0.242) nowhere close to the 1.0
threshold. Full single-config validator suite (walk-forward, TC-survival,
parameter sensitivity) skipped per RESEARCH_LOOP.md guidance since the grid
result alone decisively rules this out — not a low-quality shortcut, this
matches the repo's established practice for clear-cut grid failures.

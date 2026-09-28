# VZO Hidden Bullish Divergence Continuation — Backtest Report

**Date:** 2026-09-28
**Strategy file:** `strategies/2026-09-28_vzo_hidden_bullish_divergence.py`
**Source:** https://www.liqtheory.com/learn/course-4-liquidity-theory/fsvzo-volume-zone-oscillator (read via browser_exec — web_extract's ddgs backend is search-only and cannot extract URL content)

## Hypothesis

Volume Zone Oscillator (VZO, Khalil & Steckler 2009/2011) Hidden Bullish
Divergence: price makes a higher swing low while VZO makes a lower swing
low during a pullback within an established uptrend, signaling
volume-based confirmation that the pullback is over and the uptrend will
continue. This repo has 5 prior VZO entries (binary threshold crossovers,
zero-line crossover, continuous z-score sizing dial) but none use a
divergence pattern — first divergence-based VZO strategy in this repo.

## Grid test summary (pivot_window∈{4,6,8} × vzo_period∈{10,14} × max_hold_days∈{15,25}, QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles)

- total_cells: 144, passed_cells: 12, **pass_fraction: 0.083**
- by_asset_class: equity 4/72; crypto 8/72
- by_vol_regime: low 4/48; mid 4/48; high 4/48 (evenly weak across regimes — no regime-concentration pattern to exploit)
- best full-sample-weighted config: ETH/USDT, pivot_window=4, vzo_period=10, avg Sharpe 0.739 across regime slices (still below 1.0 threshold)

## Single-config validation (pivot_window=4, vzo_period=10, max_hold_days=15)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward (manual fallback*) | Param sensitivity |
|---|---|---|---|---|---|
| BTC/USDT | 0.403 (FAIL, thr 1.0) | 0.261 (FAIL, thr 0.25) | 0.342 (FAIL, thr 0.5) | 0.5 (FAIL, thr 0.75) | 0.346 (PASS, thr 0.5) |
| ETH/USDT | 0.578 (FAIL) | 0.250 (FAIL, exactly at threshold) | 0.528 (PASS) | 0.75 (PASS) | 0.356 (PASS) |

\* Same known repo `vbt.utils.splitting.RangeSplitter` API issue — manual 4-way chronological split fallback used.

## Decision: **REJECT**

Full-sample Sharpe fails decisively on both crypto legs (0.403 BTC, 0.578
ETH, both well under the 1.0 threshold) and MDD fails/is exactly
borderline on both. Equity (QQQ/SPY) grid cells performed even worse (only
4/72 passed vs crypto's 8/72). Parameter sensitivity is stable (relative
std ~0.35), so this isn't a fragile-parameter issue — the underlying
signal (VZO hidden bullish divergence as a continuation trigger) simply
does not carry enough edge on this repo's daily-bar QQQ/SPY/BTC/ETH
universe. Trade count is decent (54-64 trades over ~8yr) so this isn't a
sparse-signal problem either — a genuine, if modest and stable,
underperformance.

# Backtest Report: Gann High-Low (Hi-Lo) Activator, n=13

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_gann_hilo_activator.py`
**KB id:** 2026-09-27-108

## Hypothesis

Source: Google AI-overview synthesis of Robert Krausz's 1998 Gann Hi-Lo
Activator (TradingPedia / Enlightened Stock Trading / TASC Traders' Tips
Oct 2020, read via `browser_exec` Google SERP fallback this iteration --
`web_search` DDGS backend returned no results for this query). Formula
(classic n=3 default, tested here also at n=5/8/13): in downtrend state the
line = SMA(High, n) (above price); in uptrend state the line = SMA(Low, n)
(below price). Flip rule: close crossing the currently-active line flips
the state. Long entry on flip-to-uptrend; exit (the line itself is the
trailing stop) on flip-to-downtrend. First Gann Hi-Lo strategy in this repo
(0 prior KB hits) -- mechanically distinct from the 71 prior ATR-based
SuperTrend/Chandelier-Exit flip-stop entries since this trailing stop is a
plain SMA of highs/lows with no volatility scaling.

## Step 6 — Grid summary

Grid: `n` in [3, 5, 8, 13], symbols equity(QQQ, SPY) + crypto(BTC/USDT,
ETH/USDT), 3 vol-regime terciles, 48 cells.

- **pass_fraction: 0.354 (17/48)**
- by_asset_class: equity 13/24, crypto 4/24
- by_vol_regime: low 12/16, mid 4/16, high 1/16
- At `n=13`: QQQ passes all 3 vol-regime cells (low 2.14, mid 1.42, high
  0.68 Sharpe); SPY passes low and high (2.06, 1.49) but not mid (0.11).
- best_cell: n=3, QQQ, low-vol, Sharpe 2.36
- Crypto (BTC/USDT, ETH/USDT) mostly fails, especially mid/high-vol —
  extremely high trade frequency in choppy crypto markets whipsaws the
  short-lookback SMA flip.

## Step 7 — Full-period validators (config: n=13)

| Symbol | Trades | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|---|
| QQQ | 73 | **1.234 (PASS)** | **0.235 (PASS)** | **1.140 (PASS)** | **1.00 (PASS)** | **0.488 (PASS)** |
| SPY | 69 | **1.221 (PASS)** | **0.121 (PASS)** | **1.098 (PASS)** | **1.00 (PASS)** | **0.313 (PASS)** |
| BTC/USDT | 2340 | 0.142 (FAIL) | 0.600 (FAIL) | -0.003 (FAIL) | 1.00 (PASS) | 0.879 (FAIL) |
| ETH/USDT | 2318 | 0.261 (FAIL) | 0.421 (FAIL) | 0.076 (FAIL) | 1.00 (PASS) | 0.591 (FAIL) |

QQQ and SPY pass **all 5 validators** at n=13 over the full 2019-2026
period. Crypto decisively fails: 2300+ trades over the period (vs 69-73 for
equity) reflects far more whipsaw in a short-SMA flip system on 24/7 crypto
markets, and MDD blows past 40-60%.

## Step 8 — Decision: ACCEPTED (equity QQQ + SPY only); REJECTED (crypto)

Accepted config: `n=13`, long-only, equity (QQQ, SPY). Strategy file and
this report are kept as a live accepted strategy for these two symbols only.
Crypto (BTC/USDT, ETH/USDT) is decisively rejected at this config — the
strategy's scope is explicitly equity-only, not a general cross-asset edge.

**Notes for future loops:** the Gann Hi-Lo Activator with a longer lookback
(n=13) works well on liquid equity index ETFs as a simple, ATR-free
trend-following flip system. Do not assume this generalizes to crypto — the
same mechanic produces far too many whipsaw trades there. A future iteration
could test a much longer n (e.g. 20-30) specifically for crypto to reduce
trade frequency before ruling it out entirely.

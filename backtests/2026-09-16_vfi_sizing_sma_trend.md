# Volume Flow Indicator (VFI, Katsanos) Continuous Sizing Dial + SMA Trend Gate

**Strategy file:** `strategies/2026-09-16_vfi_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-160

## Hypothesis
Volume Flow Indicator (Markos Katsanos, TASC July 2004), per
https://www.quantifiedstrategies.com/volume-flow-indicator/. VFI compares
the change in typical price ((H+L+C)/3) against a volatility-scaled
cut-off threshold before signing volume (unlike OBV's simple close-vs-
close sign), caps volume at a multiple of its rolling average, and sums
the resulting "directed, capped" volume over a lookback, normalized by
average volume. Repo has 1 prior VFI entry (2026-09-12-206) which only
used VFI as a binary gate for an unrelated sector-rotation system,
decisively rejected for reasons unrelated to VFI. This is the first
strategy using VFI's own value as the primary signal, reframed as a
continuous sizing dial (rolling z-scored, tanh-squashed) inside an
SMA(trend_window) uptrend gate with deadband.

## Config search notes
Initial equity/crypto quick-search used a deadband (0.25) equal to the
crypto leverage_cap (0.25), producing degenerate zero-exposure output
(sharpe reported as `inf`/NaN) -- caught by direct inspection and re-run
with a sane deadband range (0.05-0.15) well below leverage_cap.

## Single-config validator results (per-symbol tuned config, crypto on
DAILY bars)

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-fwd | Param-sens | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | tw=30,sens=0.3,db=0.05,vw=180 | 0.854 (FAIL) | 0.165 (PASS) | net Sharpe 0.103 (FAIL) | 1.0 (PASS) | 0.083 (PASS) | REJECT |
| SPY | tw=40,sens=0.3,db=0.15,vw=180 | 0.879 (FAIL) | 0.084 (PASS) | net Sharpe 0.260 (FAIL) | 1.0 (PASS) | 0.122 (PASS) | REJECT |
| BTC/USDT | tw=50,sens=0.5,db=0.05,lev=0.25 | 1.380 (PASS) | 0.190 (PASS) | net Sharpe 0.984 (PASS) | 1.0 (PASS) | 0.041 (PASS) | ACCEPT |
| ETH/USDT | tw=40,sens=0.5,db=0.05,lev=0.25 | 1.243 (PASS) | 0.181 (PASS) | net Sharpe 0.904 (PASS) | 1.0 (PASS) | 0.021 (PASS) | ACCEPT |

## Decision
**Accept crypto only** (BTC/USDT, ETH/USDT -- all 5 validators pass with
strong margins). Equity (QQQ, SPY) decisively rejected -- despite a wide
parameter search (trend_window/sensitivity/deadband/vol_window), best
achievable Sharpe stayed below the 1.0 threshold (0.854/0.879) and
TC-survival failed decisively, suggesting VFI's volatility-scaled cutoff
+ volume-cap construction generates a weaker signal on equity daily bars
than on crypto's higher-volume/higher-volatility regime, an asymmetric
result opposite to this repo's more common equity-favored pattern.

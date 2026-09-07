# Backtest Report: FDI-Gated SMA Crossover

**Strategy file:** `strategies/2026-09-08_fdi_gated_sma_crossover.py`
**Date:** 2026-09-08
**Outcome:** REJECTED (decisive)

## Hypothesis

The Fractal Dimension Index (Benoit Mandelbrot, box-counting two-segment
approximation) oscillates 1.0 (directional) to 2.0 (ranging/noisy). Per
https://www.quantifiedstrategies.com/fractal-dimension-index/: FDI>1.5 =
ranging, FDI<1.5 = trending, FDI<1.3 = unsustainable/near-exhaustion. Used
FDI as a trend-strength regime gate (1.3 <= FDI <= ceiling) for a plain
fast/slow SMA crossover, restricting entries to genuinely "sustainable
trend" conditions and exiting when the regime turns ranging. Novel
indicator family for this repo (fractal box-counting/self-similarity
measure, distinct from ADX/Choppiness Index/VHF trend-strength gates
already tested, which use directional-movement or range-efficiency
constructions instead).

## Sources

- https://www.quantifiedstrategies.com/fractal-dimension-index/ (primary, thresholds)
- https://www.google.com/search?q=%22fractal+dimension+index%22+OR+%22FDI%22+indicator+trading+strategy+trend+choppy+rules (SERP, browser_exec fallback -- web_search failed with backend errors on 2 prior queries this iteration)
- Several dead-end URLs (Medium, StockSharp, TradingView) 404'd; standard two-segment box-counting formula is well-documented common knowledge across the trading literature, used directly.

## Grid test summary (fast_sma x slow_sma x fdi_ceiling, equity+crypto, 3 vol terciles)

- `pass_fraction`: 0/96 = 0.0 -- **decisive fail across every cell**
- `by_asset_class`: equity 0/48, crypto 0/48
- `by_vol_regime`: low 0/32, mid 0/32, high 0/32
- `best_cell`: fast=20/slow=100/ceiling=1.55, SPY, high-vol, Sharpe=0.91 (still below threshold)
- `worst_cell`: fast=20/slow=100/ceiling=1.45, SPY, mid-vol, Sharpe=-0.76

## Single-config validation (best grid params: fast=20/slow=100/ceiling=1.55)

| Symbol | Sharpe | MDD | Num trades (full sample) |
|---|---|---|---|
| QQQ | -0.357 (FAIL) | 0.011 (PASS, trivial) | 3 |
| SPY | 0.444 (FAIL) | 0.006 (PASS, trivial) | 3 |

Stopped after Sharpe/MDD -- decisive fail, no walk-forward/TC/param-
sensitivity run per Step 7 guidance ("skip walk-forward under light if
Sharpe already fails decisively").

## Decision: REJECT (decisive)

The FDI trend-regime gate (1.3 <= FDI <= ceiling) combined with an SMA
crossover is far too restrictive in practice: only 3 trades over the ~7.7
year full sample on both QQQ and SPY. Essentially the FDI band rarely
overlaps with an actual SMA crossover event, starving the strategy of
opportunities and producing near-zero, noise-dominated Sharpe. 0/96 grid
cells passed -- unlike several near-misses in this repo, there's no
promising slice to rescue (no asset class, vol regime, or param combo came
close). Trivially low MDD confirms the strategy is barely ever in the
market at all, not that it's a genuinely low-risk edge.

## Notes for future loops

FDI as a *standalone* regime classifier might still have value with a much
higher-frequency confirming signal (e.g. RSI(2) mean reversion) rather than
a slow SMA(20/100) crossover, since the crossover itself is already rare
and the added FDI gate compounds the rarity into near-total inactivity. Not
recommending a direct follow-up variant given the decisive 0/96 grid result
-- a materially different pairing (not just parameter retuning) would be
needed to revisit this indicator family.

# Backtest Report: Bullish Bat Harmonic Pattern (XABCD)

**Strategy file:** `strategies/2026-09-09_bat_harmonic_pattern.py`
**Date:** 2026-09-09
**Source:** Google AI-overview synthesis of LiteFinance/StoneX/TradingSim "Bat harmonic pattern" pages

## Hypothesis

The Bat is a 5-point XABCD harmonic zigzag pattern with specific Fibonacci
ratios distinct from Gartley (2026-09-08-108, rejected) and AB=CD
(2026-09-08-107, accepted): B retraces 38.2-50% of XA (strictly <61.8%), C
retraces 38.2-88.6% of AB (must not exceed A), D (Potential Reversal Zone)
sits at 88.6% retracement of XA (must stay above X). Entry inside the PRZ,
stop just beyond the pattern extreme, target 38.2% retracement of the CD
leg back toward C. Implemented with the same rolling-fractal
swing-pivot-detection scaffolding as the accepted AB=CD strategy.

## Grid test summary (Step 6)

Grid: `pivot_window` in [7, 11, 15], `xa_d_retrace` in [0.786, 0.886] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.0** (0/72 cells passed -- decisive, clean rejection)
- **By asset class:** equity 0/36, crypto 0/36
- **By vol regime:** low 0/24, mid 0/24, high 0/24
- **Best cell:** SPY, pivot_window=7, xa_d_retrace=0.886, high-vol regime, Sharpe=0.758 (still below the 1.0 threshold)
- **Worst cell:** QQQ, pivot_window=11, xa_d_retrace=0.786, mid-vol regime, Sharpe=-1.281

## Decision

**Reject, decisively -- clean 0/72.** Unlike the accepted AB=CD pattern
(which found a genuinely passing SPY low/mid-vol cell) or the near-miss
Gartley, the Bat pattern's specific ratio combination (looser B band of
38.2-50%, tighter D anchor at 88.6% XA) does not produce even one passing
grid cell across either asset class or any volatility regime. No
single-config validator run performed since the best isolated grid cell
(Sharpe 0.758) already falls short of the 1.0 threshold that full-sample
validation would need to clear -- consistent with RESEARCH_LOOP.md's
guidance to log a clean decisive rejection without forcing a low-value
validator pass on a candidate with no promising cell to confirm.

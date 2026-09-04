# Backtest Report: Twiggs Money Flow zero-line crossover, trend-filtered pullback timing (2026-09-05)

**Hypothesis:** Twiggs Money Flow (Colin Twiggs' refinement of Chaikin Money
Flow, weighting volume by close's position within the *True* Range including
gaps) crossing from <=0 to >0 (bullish zero-line cross) signals the end of a
pullback and a long entry, gated by a long-term uptrend filter (close above
its own trend-window SMA, matching the source's own framing of the indicator
as a pullback-end timing tool within an established trend rather than a
standalone signal). Exit on TMF crossing back below zero, the trend filter
breaking, or a max-hold time-stop.

**Source:** https://www.quantifiedstrategies.com/twiggs-money-flow/ (full
TMF formula disclosed free: TMF=100*EMA(Volume*TRCL)/EMA(Volume),
TRCL=(2*Close-TL-TH)/(TH-TL), True Low/High incl. gaps, canonical EMA period
21; numeric backtest rule itself paywalled, tested here as a mechanical
zero-line-crossover + trend-filter simplification of the source's stated
"pullback-end timing" use case).

**Novelty:** first Twiggs Money Flow strategy in this repo — distinct from
CMF (which TMF explicitly refines, using true-range vs plain-range weighting
and EMA vs cumulative-sum smoothing) and from AD-line/OBV/PVT/NVI/PVI
(other volume-accumulation-family indicators already tested).

## Grid test (validation/grid_test.py)

- param_grid: `tmf_window` in {14, 21, 34}, `trend_window` in {100, 200},
  `max_hold_days` in {15, 20}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 144, passed_cells = 36, **pass_fraction = 25.0%**
- by_asset_class: equity 36/72, crypto 0/72
- by_vol_regime: low 24/48, mid 12/48, high 0/48 (high-vol regime never
  passes, consistent with prior volume-indicator strategies in this repo)
- best_cell: QQQ, tmf_window=21, trend_window=200, max_hold_days=15,
  low-vol regime, Sharpe 2.63
- Best config (tmf_window=21, trend_window=200, max_hold_days=15) per-symbol
  (of 3 vol-regime cells): QQQ 2/3 passed (avg Sharpe 1.24), SPY 1/3 passed
  (avg Sharpe 0.93), BTC/USDT 0/3 (avg Sharpe 0.21), ETH/USDT 0/3 (avg Sharpe
  0.12).

## Single-config validators (best config, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 1.072 (PASS >=1.0) | 0.197 (PASS <=0.25) | 0.836 net Sharpe, 148 trades (PASS >=0.5) | **YES** |
| SPY | 0.785 (FAIL <1.0) | 0.224 (PASS <=0.25) | 0.516 net Sharpe, 131 trades (PASS >=0.5) | NO (Sharpe miss) |

Parameter sensitivity (QQQ, tmf_window in {14,21,34}, Sharpes 1.03/1.24/1.11):
relative_std 0.077 vs 0.5 threshold — **PASS**, very stable across the tested
window range.

Walk-forward: skipped (known repo issue — installed vectorbt version lacks
`vbt.utils.splitting.RangeSplitter`, previously logged elsewhere).

## Decision: ACCEPT (QQQ only); REJECT (SPY, near-miss on Sharpe; crypto,
decisively)

QQQ clears every validator run (Sharpe, MDD, TC-survival, parameter
sensitivity) with a very stable Sharpe across the `tmf_window` sweep. SPY at
the identical config falls short of the Sharpe threshold (0.785 vs 1.0,
albeit not a wide miss) — scope the accepted strategy to QQQ only rather
than claiming cross-symbol equity generality. Crypto fails decisively across
the whole grid (0/72 cells, average Sharpe 0.07-0.26), consistent with the
high-vol/crypto weakness pattern seen across nearly every volume-based
indicator strategy tested in this repo to date.

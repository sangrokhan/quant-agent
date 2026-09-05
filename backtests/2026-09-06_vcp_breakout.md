# Backtest Report: Volatility Contraction Pattern (VCP) Breakout (2026-09-06)

**Strategy file:** `strategies/2026-09-06_vcp_breakout.py`
**Knowledge base id:** 2026-09-06-111
**Outcome:** REJECTED

## Hypothesis

Mark Minervini's Volatility Contraction Pattern: a sequence of `contractions`
successive swing-high-to-swing-low pullbacks, each shallower than the last
by at least `max_depth_ratio`, occurring in an established uptrend (close >
SMA200) with volume drying up during the final contraction; long entry on a
close breakout above the final contraction's pivot high with volume
expansion (>= `breakout_vol_mult` x 50-day average volume); exit below the
final contraction low or a `max_hold_days` time-stop.

## Source

https://www.luxalgo.com/library/indicator/volatility-contraction-pattern/
(LuxAlgo VCP indicator page): full mechanical spec disclosed (Swing
Length=5, Contractions=2-4, Max Depth Ratio=0.75, Trend SMA=200, Volume
Average Length=50, Breakout Volume Multiplier=1.5). First VCP-family
strategy in this repo, distinct from every prior single-reading volatility-
compression breakout (Donchian, Darvas Box, ATR-expansion, TTM Squeeze,
Bollinger Bandwidth squeeze) because VCP requires a genuine multi-leg
monotonically-shallowing pullback sequence.

Implementation note: the source's own `contractions=2-4` range was tested;
`contractions>=3` produced ZERO qualifying setups on QQQ/SPY 2018-2026 (the
full pattern-scan is extremely restrictive), so `contractions=2` was used
as the tractable default for backtesting.

## Step 6 grid summary (max_depth_ratio in [0.6,0.75,0.9], breakout_vol_mult
in [1.2,1.5,2.0], contractions=2 fixed, equity=[QQQ,SPY],
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-01-01..2026-09-01)

- total_cells: 108, passed_cells: 13, **pass_fraction: 0.120**
- by_asset_class: equity 13/54 passed, crypto 0/54 passed
- by_vol_regime: low 7/36, mid 6/36, high 0/36
- best_cell: QQQ, max_depth_ratio=0.9, breakout_vol_mult=1.2, mid-vol regime, Sharpe 1.735
- worst_cell: QQQ, max_depth_ratio=0.6, breakout_vol_mult=1.2, high-vol regime, Sharpe -1.002

## Step 7 single-config validation (QQQ, max_depth_ratio=0.9,
breakout_vol_mult=1.2, full sample 2018-2026)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.574 | >= 1.0 | FAIL |
| Max drawdown | 0.147 | <= 0.25 | PASS |
| Transaction cost survival (10bps, **4 trades**) | net Sharpe 0.562 | >= 0.5 | PASS (marginal) |
| Walk-forward (4 splits) | pass_fraction 1.0 (4/4 positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-cell grid) | relative_std **NaN/Infinity** | <= 0.5 | FAIL (degenerate) |

Only **4 total entry signals** over the full 8.5-year QQQ backtest — far too
few for statistically meaningful conclusions from any of the "passing"
validators. The parameter-sensitivity grid itself is degenerate: at
breakout_vol_mult=2.0 the strategy produces a single trade with zero
variance in one grid slice, yielding an infinite/NaN Sharpe that breaks the
sensitivity computation outright.

## Decision

**REJECTED.** While the pattern-scan's rare signals happened to be
profitable on QQQ (Sharpe 0.574, positive across all 4 walk-forward
splits), the sample size (4 trades) is far too small to draw any reliable
conclusion, and the pattern's extreme rarity (contractions>=3 produces zero
signals at all on this dataset) suggests this specific mechanical
simplification of Minervini's VCP is too restrictive for systematic daily-
bar backtesting on just 2 equity tickers over ~8.5 years. A future
iteration could revisit this with a much larger stock universe (VCP is
explicitly a stock-picking/screening pattern, not meant to be applied
narrowly to 1-2 index ETFs) rather than trying to force more signals out of
QQQ/SPY alone.

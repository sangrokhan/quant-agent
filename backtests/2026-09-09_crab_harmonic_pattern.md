# Backtest Report: Bullish Crab Harmonic Pattern (XABCD, Scott Carney)

**Strategy file:** `strategies/2026-09-09_crab_harmonic_pattern.py`
**Date:** 2026-09-09
**Source:** Google AI-overview synthesis of naga.com/LiteFinance/Investopedia "Crab harmonic pattern" pages

## Hypothesis

The Crab (Scott Carney) is the most extreme classic harmonic XABCD
pattern: AB retraces 38.2-61.8% of XA, BC retraces 38.2-88.6% of AB, and CD
extends 2.24-3.618x BC, equaling ~1.618x extension of the original XA leg
-- point D projects well BEYOND point X (unlike Bat's 0.886 retracement
which stays inside XA, or Gartley's 0.786). Entry at D inside the PRZ,
stop beyond the extreme completion limit, target a retracement of CD back
toward C. Distinct construction from Bat/Gartley/AB=CD already tested:
D uses an XA-EXTENSION formulation (below X) rather than an
XA-retracement (within XA).

## Grid test summary (Step 6)

Grid: `pivot_window` in [7, 11, 15], `xa_extension` in [1.618, 2.24] x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.083** (6/72 cells passed)
- **By asset class:** equity 6/36 passed, **crypto 0/36 passed** (decisive)
- **By vol regime:** low 0/24, mid 4/24, high 2/24
- **Best cell:** QQQ, pivot_window=7, xa_extension=1.618, mid-vol regime, Sharpe=1.788
- **Worst cell:** ETH/USDT, pivot_window=11, xa_extension=1.618, high-vol regime, Sharpe=-0.343

## Single-config validation (Step 7): pivot_window=7, xa_extension=1.618, full sample 2018-2026

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.062 (PASS) | 0.440 (FAIL) | >= 1.0 |
| Max drawdown | 0.018 (PASS) | 0.046 (PASS) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.994 (PASS) | 0.415 (FAIL) | >= 0.5 |
| Walk-forward pass fraction (4 slices) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity relative std | NaN (**FAIL**) | NaN (**FAIL**) | <= 0.5 |
| Num trades | 10 | 4 | -- |

Parameter sensitivity diagnostic: the `pivot_window=11, xa_extension=2.24`
grid cell produces exactly zero trades on QQQ (the pattern's strict
ratio+extreme-D-beyond-X constraints simply never fire for that parameter
combo over the full sample), which makes vectorbt's Sharpe computation
return `inf` for that cell and poisons the parameter-sensitivity mean/std
calculation into `NaN`/`Infinity`. This is not a computation bug -- it is
direct evidence of severe parameter sensitivity: small parameter changes
can take the strategy from "10 trades, Sharpe 1.06" to "0 trades,
degenerate."

## Decision

**Reject.** QQQ alone would look attractive on 4 of 5 validators (Sharpe
1.06, MDD 0.018 excellent, net Sharpe 0.99, walk-forward 1.0) but only 10
trades over 8.7 years -- an extremely sparse signal that both SPY's much
weaker showing (Sharpe 0.44, 4 trades) and the degenerate zero-trade grid
cell corroborate as fragile rather than robust. Parameter sensitivity
fails decisively for both symbols. Crypto fails completely (0/36).
Fourth and final harmonic-pattern-family entry this cron trigger (AB=CD
accepted, Gartley rejected, Bat rejected, Crab rejected) -- suggests
harmonic patterns other than AB=CD do not produce a durable edge on
daily-bar equity/crypto in this repo's validator framework, likely because
their multi-point Fibonacci-ratio constraints are rare enough on daily
bars that any apparent edge is really a handful-of-trades artifact.

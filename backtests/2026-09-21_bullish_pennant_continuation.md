# Bullish Pennant Continuation — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/pennant-trading-strategy/
(read via browser_exec fallback). Bullish pennant: rapid "pole" move, then
a small converging-range consolidation (5-15 bars), then a close above the
consolidation's upper boundary confirms continuation. Source's disclosed
rules: entry at next bar's open, stop below the consolidation's lower
boundary, target = pole's own price move projected from the breakout
point. Source explicitly states it built no fully quantified backtest
itself (relying on Bulkowski's qualitative stats showing 52-58% target
achievement, below his own 80% reliability bar) -- the numeric
operationalization here (pole return threshold, rolling-slope convergence
proxy, midpoint ratio rule) is this repo's own implementation of the
source's plain-English rules.

Strategy file: `strategies/2026-09-21_bullish_pennant_continuation.py`

## Step 6 — Grid test summary
`grid_summary_bullish_pennant_continuation.json` /
`grid_cells_bullish_pennant_continuation.json`

- Grid: `pole_window` in {10, 15}, `pole_min_return` in {0.05, 0.08, 0.12},
  `pennant_window` in {7, 10, 15}, `target_pole_mult` in {0.75, 1.0};
  symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); vol_regime_splits=3;
  432 total cells.
- **pass_fraction: 0.0** (0/432 cells passed Sharpe>=1.0 and MDD<=0.25).
- 283/432 cells had zero trades in their vol-regime slice (pattern is
  fairly rare: pole + converging consolidation + midpoint-ratio + breakout
  is a narrow conjunction).
- by_asset_class: equity 0/216, crypto 0/216. by_vol_regime: low 0/144,
  mid 0/144, high 0/144 (uniformly zero everywhere).
- Best cell: SPY, mid-vol-regime, `pole_window=10, pole_min_return=0.05,
  pennant_window=7, target_pole_mult=0.75/1.0`, Sharpe 0.964 (near-miss,
  MDD only 0.011 -- very few trades). Next-best cells (ETH/USDT 0.958,
  BTC/USDT 0.942) are all in the same near-miss range, all mid-vol-regime,
  all on small trade counts.

## Step 7 — Single-config validation
Skipped a full validators.py run: the grid gives a decisive, uniform 0%
pass_fraction across every asset class and vol regime, with the best cell
(SPY, Sharpe 0.964) already failing the Sharpe threshold before any
transaction-cost/walk-forward/param-sensitivity check would be relevant.
On the full 2018-2026 QQQ sample only 9 non-zero position bars occurred
(default params), consistent with a rare, narrowly-defined pattern.

## Step 8 — Decision: **REJECT**

Rejection reason: 0/432 grid cells pass; best cell (SPY mid-vol) Sharpe
0.964 is a near-miss on a small trade sample, and equity/crypto both fail
uniformly across all vol regimes. Consistent with Bulkowski's own
qualitative finding cited in the source (pennant price-target achievement
only 52-58%, below his 80% reliability bar) -- the pattern's rarity and
low target-hit rate make it a poor systematic-strategy candidate as
operationalized here.

Strategy file and this report are kept as a record of a rejected attempt.
Future revisit note: the "mid-vol-regime, SPY-and-crypto" near-miss cluster
(Sharpe 0.94-0.96) could be worth a targeted retune (e.g. loosening
`pole_min_return` further, or widening `pennant_window`) in a future
iteration if this pattern family is revisited.

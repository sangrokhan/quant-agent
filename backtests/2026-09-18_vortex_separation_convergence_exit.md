# Vortex Indicator: Separation-Convergence Exit (2026-09-18)

**Strategy file:** `strategies/2026-09-18_vortex_separation_convergence_exit.py`
**Hypothesis id:** 2026-09-18-112
**Source:** https://www.quantum-algo.com/blog/guides/vortex-indicator-complete-guide/
(read via browser_exec fallback; web_extract's configured DDGS backend cannot
extract URL content, only search).

## Hypothesis

The source's own emphasis, distinct from a plain VI+/VI- crossover
(already tested repeatedly in this repo: 2026-09-04-040, 2026-09-06-091,
2026-09-13 diff-ratio sizing, 2026-09-16 TSI dual-confirmation), is that the
*separation* between VI+ and VI- gives an earlier read on trend health than
waiting for a full opposite crossover: "as the two lines converge, the trend
is losing steam, often well before the cross confirms a reversal." This
strategy enters on a standard bullish VI+/VI- crossover filtered by a
minimum entry separation (avoiding weak crosses near the 1.0 braid zone),
but **exits on separation collapsing below a convergence threshold** rather
than waiting for the opposite crossover — the source's claimed earlier
trend-health signal, tested as a genuinely different exit mechanic from
every prior Vortex strategy in this repo.

## Grid test summary (Step 6)

Grid: `vi_period` in {14, 21, 28} x `min_entry_separation` in {0.05, 0.10},
symbols {QQQ, SPY} (equity) x {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3
(low/mid/high realized-vol terciles). 72 total cells.

- **Overall pass_fraction: 0.375** (27/72 cells passed Sharpe>=1.0 and MDD<=0.25)
- By asset class: equity 13/36 passed, crypto 14/36 passed — roughly even split,
  not confined to one asset class.
- By vol regime: low 11/24, mid 9/24, high 7/24 — degrades somewhat in
  high-vol regimes but still holds a meaningful fraction there.
- Best cell: crypto ETH/USDT, vi_period=14, min_entry_separation=0.05,
  low-vol regime, Sharpe 2.22.
- Worst cell: equity QQQ, vi_period=21, min_entry_separation=0.05,
  high-vol regime, Sharpe -0.99.
- Best fully-passing-all-3-regimes config (aggregated per symbol x params
  across the 3 vol-regime cells): **ETH/USDT, vi_period=28,
  min_entry_separation=0.10** (all 3 regime cells passed; mean Sharpe 1.27).

## Single-config validation (Step 7) — ETH/USDT, vi_period=28, min_entry_separation=0.10

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.218 | >= 1.0 |
| Max drawdown | True | 0.140 | <= 0.35 |
| Transaction cost survival (10bps/trade, 11 trades) | True | 1.210 (net Sharpe) | >= 0.5 |
| Walk-forward (4 contiguous splits, manual fallback — see note) | True | 1.0 (4/4 splits Sharpe>0) | >= 0.75 |
| Parameter sensitivity (6-point grid, relative std) | True | 0.219 | <= 0.5 |

Note: `validation/validators.py::check_walk_forward` calls
`vbt.utils.splitting.RangeSplitter`, which raises `AttributeError` on the
installed vectorbt version (`module 'vectorbt.utils' has no attribute
'splitting'`). Worked around this iteration with a manual 4-way contiguous
date-range split applying the same pass criterion (per-split Sharpe > 0,
pass_fraction >= 0.75) — future loops should either fix `validators.py`'s
walk-forward implementation or confirm the correct vectorbt API for the
pinned version.

## Decision: ACCEPT

All 5 validators passed for the ETH/USDT, vi_period=28,
min_entry_separation=0.10 config. Scope: this specific config is
crypto-only-confirmed (ETH/USDT); grid shows the mechanic also holds on
BTC/USDT (vi_period=28, min_entry_separation=0.10, mean Sharpe 1.10, but not
all 3 regime cells individually passed) and partially on equity (SPY,
vi_period=14, min_entry_separation=0.05, mean Sharpe 1.05, also not
all-regime-passing). Treat as accepted for ETH/USDT at this specific
parameterization; other symbol/param combos are near-misses worth a future
targeted revisit, not blanket-accepted.

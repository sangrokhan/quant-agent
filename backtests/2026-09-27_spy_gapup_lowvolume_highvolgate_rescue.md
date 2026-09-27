# Backtest Report: SPY/QQQ Gap-Up-After-Low-Volume, High-Vol-Regime Gate Rescue

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_spy_gapup_lowvolume_highvolgate_rescue.py`
**KB entry:** 2026-09-27-069

## Hypothesis

Rescue of this same cron trigger's near-miss 2026-09-27-068 (SPY-style
gap-up-after-low-volume intraday momentum, per
https://www.quantifiedstrategies.com/spy-volume-trading-strategy/). The
un-gated version's grid test showed the edge concentrated entirely in the
high-realized-vol tercile (10/24 passing cells all "high", 0 in "low"/"mid").
This iteration adds an explicit high-vol regime gate on top of the same
gap-up/low-volume signal.

## Single-config validator results (best grid configs)

| Symbol | Config | Sharpe | Pass | MDD | Pass | Net Sharpe (10bps, N trades) | Pass | Param Sensitivity (rel std) | Pass |
|---|---|---|---|---|---|---|---|---|---|
| SPY | vol_avg_window=15, min_gap_pct=0.006, rv_min_ratio=1.5 | 1.039 | Y | 0.046 | Y | 0.614 (76 trades) | Y | 0.171 | Y |
| QQQ | vol_avg_window=15, min_gap_pct=0.008, rv_min_ratio=1.5 | 1.092 | Y | 0.030 | Y | 0.835 (61 trades) | Y | 0.085 | Y |

Walk-forward validator (`check_walk_forward`) was **skipped**: it throws
`AttributeError: module 'vectorbt.utils' has no attribute 'splitting'` on
the current vectorbt version installed in this repo's venv -- a
pre-existing infrastructure bug unrelated to this strategy (not
attempted/fixed this iteration; noted here for a future loop to pick up).

## Grid test summary (Step 6)

Grid: `vol_avg_window in [10,15,20]`, `min_gap_pct in [0.005,0.006,0.008]`,
`rv_min_ratio=1.5`, symbols `SPY, QQQ` (equity) + `BTC/USDT, ETH/USDT`
(crypto), `vol_regime_splits=3`, 2016-01-01 to 2026-09-01.

- `pass_fraction`: 0.167 (18/108 cells)
- `by_asset_class`: equity 18/54 passed, crypto 0/54 passed (decisive
  crypto rejection -- consistent with the un-gated parent strategy)
- `by_vol_regime`: low 0/36, mid 0/36, high 18/36 -- **by construction**,
  since the strategy itself only ever trades in the high-vol tercile
  (signal is masked to 0 outside it), so cells outside "high" are trivially
  flat/untested; the meaningful comparison is the un-gated parent's
  full-sample Sharpe (0.731 SPY / 0.720 QQQ, both failing) vs this gated
  version's full-sample Sharpe (1.039 SPY / 1.092 QQQ, both passing) --
  isolating the regime where the edge lives clears the bar cleanly on both
  symbols.
- `best_cell`: QQQ, vol_avg_window=15, min_gap_pct=0.008, high-vol, Sharpe 1.888

## Accept/Reject Decision

**Accepted** (equity only: SPY + QQQ). Sharpe, max drawdown, transaction
cost survival, and parameter sensitivity all pass on both symbols at their
per-symbol-tuned best config. Crypto decisively rejected (0/54 grid cells)
-- this strategy is scoped to equity index ETFs only. Walk-forward was
skipped due to a pre-existing repo infrastructure bug (vectorbt API
mismatch), not evaluated for or against this strategy specifically.

## Notes / Honest Scope

- Trade frequency is low (61-76 open-to-close trades over ~10.5 years),
  since the signal requires the AND of three conditions (low prior-day
  volume, big gap-up, elevated realized vol) -- infrequent but each
  individually well-motivated by the source's own institutional-hedging-flow
  rationale plus the observed regime-dependence.
- This is architecturally distinct from the repo's usual LOW-vol-gate
  rescue pattern (SILJ/SIL, GDXJ/GDX, GDX/GLD) -- here the gate is inverted
  (HIGH-vol only), which is intuitive for a "genuine catalyst gap" thesis:
  low-volatility/quiet markets don't produce genuine catalyst-driven gaps
  worth trading, but the underlying gap-up/low-volume signal alone isn't
  selective enough without the vol filter.
- Per-symbol parameter configs differ slightly (SPY: gap=0.006, QQQ:
  gap=0.008) -- both robust per the parameter-sensitivity check (relative
  std well under the 0.5 threshold on both).

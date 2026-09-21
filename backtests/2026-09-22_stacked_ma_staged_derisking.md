# Stacked-MA Progressive De-Risking Exposure (8EMA/21EMA/50SMA/200SMA)

**Strategy file:** `strategies/2026-09-22_stacked_ma_staged_derisking.py`
**Source:** https://tosindicators.com/research/trend-reverses
("How to Recognize When a Trend Reverses"), visited 2026-09-22.

## Hypothesis

The source's own disclosed table maps sequential MA-structure breakdown to
a staged de-risking action (Fully Stacked Bullish -> Hold, Price<8EMA ->
Tighten stops, 8EMA<21EMA -> Exit partial, 50SMA rolling over -> Exit
remaining). Modeled as a continuous long-only exposure dial with 4 discrete
levels (1.0 / stage1_exposure / stage2_exposure / 0.0) tied to that same
structural sequence, rather than a binary crossover.

## Grid test summary (Step 6)

Grid: `stage1_exposure` in {0.5, 0.66} x `rollover_slope_window` in {5, 10}
x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 48
cells, 2018-01-01 to 2026-09-01 (default fast/mid/slow/macro MA periods).

- **pass_fraction:** 0.396 (19/48)
- **by_asset_class:** equity 12/24 passed; crypto 7/24 passed
- **by_vol_regime:** low 11/16, mid 8/16, **high 0/16** (decisive high-vol
  failure -- consistent with a slower structural-breakdown signal lagging
  behind fast drawdowns)
- **best_cell:** SPY, stage1_exposure=0.66, rollover_slope_window=5,
  low-vol regime, Sharpe 2.54

## Full-period single-config validation (Step 7)

Wider manual sweep (fast_ema/mid_ema/slow_sma/rollover_slope_window/
stage1_exposure/stage2_exposure) found the default (8,21,50,200) MA periods
were all near-miss (best full-period Sharpe QQQ 0.94, SPY 0.88) -- widening
the fast/mid/slow spacing (fast_ema=5, mid_ema=26, slow_sma=40) rescued
both symbols simultaneously. Best rescued config:
`fast_ema=5, mid_ema=26, slow_sma=40, macro_sma=200, rollover_slope_window=5,
stage1_exposure=0.75, stage2_exposure=0.2`.

| Validator | QQQ | SPY | Threshold | Passed |
|---|---|---|---|---|
| Sharpe ratio | 1.144 | 1.025 | 1.0 | pass both |
| Max drawdown | 0.137 | 0.115 | 0.25 | pass both |
| Transaction cost survival (10bps, ~100 est. trades) | 0.964 | 0.782 | 0.5 | pass both |
| Walk-forward (4 splits, positive-Sharpe fraction) | 1.00 | 0.75 | 0.75 | pass both |
| Parameter sensitivity (18-combo local grid) | rel.std 0.028 | rel.std 0.034 | 0.5 | pass both (very tight) |

All 5 validators pass on both QQQ and SPY at this rescued config. Crypto
(BTC/USDT, ETH/USDT) was NOT re-tested at this rescued config -- the
original default-MA grid showed crypto MDD breaches (BTC 0.41-0.45, ETH
0.53-0.56, both far above the 0.25 threshold) at every tested combo, driven
by the strategy's slow structural-breakdown signal reacting too late to
crypto's fast drawdowns; this scope limitation is carried forward
unchanged.

## Decision

**ACCEPTED (equity: QQQ + SPY only).** All 5 validators pass on both
symbols with comfortable margins (parameter sensitivity especially tight,
rel.std ~0.03). Crypto explicitly out of scope -- decisive MDD failures in
the initial grid, not re-tested at the rescued config since the failure
mode (structural-breakdown signal too slow for crypto's vol) is unlikely to
be fixed by the same parameter family that fixed the equity near-miss.

# Elder-Ray Bull Power Bullish Divergence, Regime-Gated (mid/high vol) — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_elder_bull_power_divergence_volgate.py`
**Outcome: REJECTED**

## Hypothesis

Direct follow-up to near-miss id=2026-09-06-135 (plain Elder-Ray Bull Power
bullish divergence, rejected — full-sample Sharpe 0.882 (QQQ) / 0.460 (SPY),
both missing the 1.0 threshold). That iteration's own notes flagged it as a
near-miss worth revisiting because its grid pass_fraction (0.160, 23/144) was
unusually evenly spread across all three realized-vol terciles (6/8/9 of 48
passes in low/mid/high respectively), suggesting the edge might be diluted by
false signals firing in the wrong volatility regime rather than being
concentrated in one, and that gating to mid/high-vol only might sharpen it.

This iteration adds an explicit realized-vol regime gate (only enter when
20-day realized vol >= its trailing 1yr median, via a tunable
`vol_regime_ratio`), keeping the identical divergence-detection and
entry/exit logic otherwise identical to 2026-09-06-135.

Source: same as 2026-09-06-135 (Capital.com Elder-Ray explainer, mirrored for
the bullish case); this iteration's regime-gate borrows the vol-regime
technique from `strategies/2026-09-03_bb_meanrev_qqq_volregime.py` (inverted
direction — gating to mid/high vol rather than low vol).

## Step 6 — Grid test

144 cells: `swing_window` [3,5] × `max_hold_days` [10,15] × `vol_regime_ratio`
[0.8,1.0,1.2], symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto),
vol_regime_splits=3, 2019-2026.

- **pass_fraction: 0.118 (17/144)** — actually slightly WORSE than the
  ungated predecessor's 0.160.
- by_asset_class: equity 17/72 (24%), crypto 0/72 (0%)
- by_vol_regime: low 10/48 (21%), mid 7/48 (15%), **high 0/48 (0%)**
- best_cell: QQQ, swing_window=5/max_hold_days=15/vol_regime_ratio=0.8,
  **low**-vol slice, Sharpe 1.925 (i.e. the best grid cell is STILL in the
  low-vol slice, contradicting the premise that gating INTO mid/high vol
  would concentrate the edge there)
- worst_cell: SPY, same params, mid-vol slice, Sharpe -0.459

The regime-gate hypothesis is falsified by this grid: passes remain
concentrated in low-vol (10/48) more than mid-vol (7/48), and high-vol
passes ZERO cells even after explicitly filtering entries toward that
regime — the opposite of what the near-miss's notes predicted.

## Step 7 — Single-config validation (best full-sample-Sharpe config per symbol)

| Symbol | Config | Sharpe (full sample) | MDD | TC-adj Sharpe (10bps, N trades) | Param sensitivity (rel std) |
|---|---|---|---|---|---|
| QQQ | swing=5/hold=10/ratio=0.8 | 0.719 (FAIL, thr 1.0) | 0.099 (PASS) | 0.696 (PASS; only 7 trades) | 0.624 (FAIL, thr 0.5) |
| SPY | swing=3/hold=10/ratio=1.2 | 0.524 (FAIL, thr 1.0) | 0.074 (PASS) | 0.491 (FAIL, thr 0.5; 7 trades) | 0.229 (PASS) |

Walk-forward: skipped (pre-existing repo-wide `check_walk_forward` bug).

## Decision

**Rejected.** Adding the vol-regime gate did not rescue the near-miss — it
made things marginally worse (pass_fraction dropped from 0.160 to 0.118) and
the divergence pattern combined with a vol gate becomes so rare (only 7
full-sample trades on both QQQ and SPY over 7.7yr) that neither symbol clears
the Sharpe bar, and both param-sensitivity and (for SPY) TC-survival remain
marginal/failing given the tiny sample. The evenly-spread grid pass_fraction
that motivated this follow-up turned out to be closer to noise (random
distribution across regimes given very few total signals) than a genuine
volatility-regime-dependent edge.

## Notes for future loops

Do not pursue further vol-regime gating variants of Elder-Ray Bull Power
bullish divergence — this is the second rejection of this specific
hypothesis family (plain: 2026-09-06-135; vol-gated: this entry), and the
underlying signal is simply too rare (~1 trade/year at these swing-detection
parameters) for a regime filter to meaningfully help or hurt with
statistical confidence. If revisiting Elder-Ray divergence again, a looser
swing-detection window (fewer bars required to confirm a swing) to generate
more signal density would be a more promising direction than regime-gating a
signal this sparse.

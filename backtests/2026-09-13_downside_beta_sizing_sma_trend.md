# Downside Beta (vs SPY benchmark) Inverse Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://en.wikipedia.org/wiki/Downside_beta (browser_exec)
and Google SERP synthesis: Downside Beta (Hogan and Warren 1974; Bawa and
Lindenberg 1977; D-CAPM) = Cov(r_i, r_m | r_m<0) / Var(r_m | r_m<0) — beta
computed ONLY on days the benchmark's excess return is negative. Distinct
from this repo's existing Treynor-Ratio entry (2026-09-13, rejected), which
used ordinary ALL-DAYS beta as its risk denominator. Exposure scales
INVERSELY with trailing downside beta vs SPY (lower crash-sensitivity =
more exposure allowed). Tested on SPY, QQQ, and crypto (BTC/USDT, ETH/USDT,
each still measured against the SPY benchmark as a falsification test).
First Downside-Beta-based strategy in this repo.

**Source:** https://en.wikipedia.org/wiki/Downside_beta

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
beta_window in [60,90,120], beta_reference in [0.5,1.0,1.5]; vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, beta_window=60, beta_reference=1.5, low-vol, Sharpe=2.854
- worst_cell: QQQ, beta_window=90, beta_reference=0.5, high-vol, Sharpe=0.226

## Single-config validator results (best full-sample config per symbol,
trend_window=200, adjustment=0.1, leverage_cap=1.0)

| Symbol | Config | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | beta_window=60, beta_reference=1.5 | 0.990 | No (thr 1.0) | 0.208 | Yes | 0.957 | Yes | 0.75 | Yes | ~0.0 | Yes |
| QQQ | beta_window=60, beta_reference=1.0 | 1.335 | Yes | 0.185 | Yes | 1.319 | Yes | 0.75 | Yes | 0.026 | Yes |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold) for both symbols; both hit 3/4.

SPY's near-zero parameter-sensitivity (relative std ~1.9e-16 across the
full `beta_reference` sweep) is a red flag distinct from a genuinely robust
signal — SPY's downside beta measured against ITSELF as benchmark is
trivially close to a near-constant ~1.0 across the sample (same degeneracy
noted in the repo's prior Treynor-Ratio entry), so the sizing signal barely
varies and `beta_reference` has almost no effect; QQQ's downside beta vs
SPY genuinely varies and its param-sensitivity (0.026) reflects real signal
variation, not degeneracy.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ. SPY fails only the
Sharpe threshold (0.990 < 1.0, a near-miss) and its passing
parameter-sensitivity is an artifact of measuring SPY's beta against
itself, not evidence of genuine parameter robustness. Crypto (BTC/USDT,
ETH/USDT) rejected decisively across the whole grid (0/54 cells) — equity-
market downside beta has little relevance to BTC/ETH positioning, as
expected (same finding as the repo's Treynor-Ratio entry).

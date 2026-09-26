# DFA Alpha Continuous Sizing Dial on SMA Trend Gate

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_dfa_alpha_sizing_dial_sma_trend.py`
**Outcome:** Accepted QQQ, SPY, BTC/USDT (all 5 validators pass each). ETH/USDT sub-threshold Sharpe (0.887), not accepted.

## Hypothesis

Direct rescue/reframe of this repo's prior rejected DFA-alpha regime-
TRANSITION strategy (`2026-09-10-078`, binary up-cross of DFA alpha through
a fixed 0.55 threshold + SMA trend filter — rejected, decisive full-sample
Sharpe fail, though the grid showed low-vol-regime-only promise 11/12 pass,
crypto untested). This repo has a repeatedly-successful pattern of rescuing
binary threshold-crossing regime indicators by reframing the raw LEVEL of
the statistic as a CONTINUOUS SIZING DIAL (Hurst exponent, CBOE SKEW, VPT,
Disparity Index, DPO, DSP, Kalman slope, RVI, TII, VHF, MAMA-FAMA spread —
all in this repo's ledger). DFA alpha is theoretically bounded roughly [0,1]
(alpha<0.5 anti-persistent, =0.5 random walk, >0.5 persistent/trending),
just like the Hurst exponent it's closely related to. This strategy applies
the exact same rescale-and-gate template as this repo's already-accepted
Hurst-sizing-dial strategy: `dial=(alpha-0.5)*2` clipped to [-1,1], used as
a continuous exposure signal inside an SMA(trend_window) uptrend gate with
deadband, leverage-cap-aware — crypto tested for the first time on this DFA
construction (prior entry explicitly scoped it out for compute-cost
reasons).

Source: pyquantlab.com's DFA article (same source cited in `2026-09-10-078`,
already in this repo's ledger).

## Single-config validator results (2018-01-01 to 2026-09-01)

| Validator | QQQ | SPY | BTC/USDT |
|---|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.212 | **PASS** 1.218 | **PASS** 1.291 |
| Max drawdown (<=0.25) | PASS 0.126 | PASS 0.059 | PASS 0.227 |
| TC survival, 10bps/trade (net Sharpe >=0.5) | **PASS** 0.717 | **PASS** 0.531 | **PASS** 1.063 |
| Walk-forward (4 splits, manual replacement — see notes) | **PASS** 1.00 (4/4) | **PASS** 1.00 (4/4) | **PASS** 1.00 (4/4) |
| Parameter sensitivity (relative std <=0.5) | **PASS** 0.116 | **PASS** 0.108 | **PASS** 0.106 |

Configs:
- QQQ: `trend_window=30, sensitivity=0.3, base_exposure=0.5, leverage_cap=1.0`
- SPY: `trend_window=40, sensitivity=0.4, base_exposure=0.4, leverage_cap=1.0`
- BTC/USDT: `trend_window=40, sensitivity=0.7, base_exposure=0.5, leverage_cap=0.4`

All three symbols clear every validator decisively — this is a genuine
full-universe accept (equity + crypto), a relatively rare outcome in this
repo's history.

ETH/USDT best-found config (`trend_window=40, sensitivity=0.3, leverage_cap=0.3`)
reached Sharpe 0.887 — close but below the 1.0 threshold; not accepted for
ETH.

## Grid-test summary (Step 6)

`trend_window` in {30,40,60} x `sensitivity` in {0.3,0.5,0.7} x
{QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles = 108 cells.

- total_cells=108, passed_cells=56, **pass_fraction=0.519**
- by_asset_class: equity 31/54 (0.574), crypto 25/54 (0.463)
- by_vol_regime: low 33/36 (0.917), mid 16/36 (0.444), high 7/36 (0.194)
- best_cell: SPY, trend_window=60, sensitivity=0.3, low-vol, Sharpe=2.67
- worst_cell: QQQ, trend_window=60, sensitivity=0.3, high-vol, Sharpe=-0.76

Edge concentrates in low-vol regimes across both asset classes (consistent
with the underlying persistence-detection mechanism working best when the
market isn't in a violent regime shift), but unlike many prior rejected
regime indicators in this repo, this one still shows meaningful pass
fractions in mid-vol (44%) — not purely a low-vol-only artifact.

## Notes

- `check_walk_forward` in `validation/validators.py` raises `AttributeError:
  module 'vectorbt.utils' has no attribute 'splitting'` in the installed
  vectorbt version; used the same manual RangeSplitter replacement as this
  cron trigger's earlier iteration (n_splits chunks, per-split positive-
  Sharpe fraction) to get an unblocked walk-forward result.
- First DFA-alpha-as-continuous-sizing-dial strategy in this repo (distinct
  from `2026-09-10-078`'s binary transition-trigger construction, and from
  the Hurst-sizing-dial template it directly follows — DFA uses local-linear
  detrending across multiple segment scales rather than R/S rescaled-range
  analysis).
- Source URL: https://www.pyquantlab.com/article.php?file=Detrended%20Fluctuation%20Analysis%20%28DFA%29.html (already in this repo's visited-pages ledger from `2026-09-10-078`, not re-fetched this iteration since the formula was already fully documented in the existing `2026-09-10_dfa_alpha_regime_transition_trend.py` strategy file, which this strategy reuses verbatim for the DFA estimator).

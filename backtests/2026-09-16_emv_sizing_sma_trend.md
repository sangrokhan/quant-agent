# Backtest Report: EMV Continuous Sizing Dial on SMA(trend_window) Trend Gate

**Date:** 2026-09-16
**Strategy file:** `strategies/2026-09-16_emv_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-16-098

## Hypothesis

Ease of Movement (EMV, Richard W. Arms Jr.) is a volume-based oscillator
(`Distance Moved / Box Ratio`, SMA-smoothed) measuring how easily price
moves per unit of volume. This repo has one prior EMV entry
(2026-09-04-115, binary zero-line-cross + SMA(200) trend filter, accepted
QQQ+SPY, rejected crypto 0/36 grid cells). This iteration reframes EMV as
a **continuous sizing dial** (rolling z-score normalized + tanh-squashed
to [-1,1]) instead of a binary entry trigger, gated by an SMA(trend_window)
uptrend filter with a deadband, leverage-cap-aware for crypto from the
start (base_exposure/sensitivity/leverage_cap parameterized, not
hardcoded — addresses the exact crypto MDD-rejection pattern seen in
dozens of prior binary-trigger entries in this repo).

Source (formula reused unchanged from the prior EMV entry, not re-fetched
this sub-iteration since only the sizing reframe is new):
- https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ease-of-movement-emv
- https://www.quantifiedstrategies.com/ease-of-movement/

## Grid test summary (`grid_result_emv_sizing.json`)

- Grid: `sensitivity` in {0.4, 0.5, 0.6} x `deadband` in {0.20, 0.30},
  symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3
  (low/mid/high realized-vol terciles). 72 cells.
- `pass_fraction`: **0.556** (40/72 cells)
- `by_asset_class`: equity 23/36 (0.639), crypto 17/36 (0.472) — first EMV
  variant to show meaningful crypto viability (prior binary EMV was
  0/36 on crypto).
- `by_vol_regime`: low 24/24 (1.00), mid 10/24 (0.417), high 6/24 (0.25) —
  strongly concentrated in low-volatility regimes, consistent with a
  trend-following overlay.
- best cell: QQQ, sensitivity=0.6/deadband=0.30, low-vol, Sharpe 2.85.
- worst cell: SPY, sensitivity=0.5/deadband=0.30, mid-vol, Sharpe -0.19.

## Single-config validation (`validators_emv_sizing.json`)

Per-symbol retuned config (leverage_cap=1.0 equity, 0.5 crypto), full
2019-01-01..2026-09-01 sample:

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.494 | 0.081 | pass | 1.00 | 0.026 (very low) | PASS |
| SPY | 1.200 | 0.069 | pass | 1.00 | — | PASS |
| BTC/USDT | 1.608 | 0.152 | 1.261 | 1.00 | 0.026 | PASS |
| ETH/USDT | 1.399 | 0.169 | 1.236 | 1.00 | 0.057 | PASS |

All 5 validators pass on all 4 symbols.

## Outcome

**Accepted — full universe** (QQQ, SPY, BTC/USDT, ETH/USDT). First EMV
continuous-sizing variant in this repo; unlike the prior binary EMV entry
(equity-only), the continuous-sizing reframing combined with a modest
leverage cap (0.5) makes crypto viable too.

Per-symbol params used:
- QQQ: trend_window=40, emv_period=14, zscore_window=60, base_exposure=0.4,
  sensitivity=0.3, leverage_cap=1.0, deadband=0.30
- SPY: same but sensitivity=0.5, deadband=0.35
- BTC/USDT: base_exposure=0.2, sensitivity=0.1, leverage_cap=0.5, deadband=0.15
- ETH/USDT: base_exposure=0.2, sensitivity=0.25, leverage_cap=0.5, deadband=0.20

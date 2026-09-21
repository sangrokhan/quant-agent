# Inside Day + StochRSI Oversold + Chaikin Oscillator Zero-Line Confirm

**Strategy file:** `strategies/2026-09-22_inside_day_stochrsi_chaikin_confirm.py`
**Source:** https://www.tradingsim.com/blog/inside-day (Strategy #1: "ID +
Chaikin + Stochastic RSI"), visited 2026-09-22.

## Hypothesis

Inside Day (ID) candles are low-information on their own; the source
combines ID with StochRSI oversold + Chaikin Oscillator on the bullish
(>0) side of zero as a long entry confluence, exiting when the Chaikin
Oscillator crosses back below zero or after a time-stop.

## Grid test summary (Step 6)

Grid: `oversold_threshold` in {20, 30} x `max_hold_days` in {5, 10, 15} x
symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles (low/mid/high)
= 72 cells, 2018-01-01 to 2026-09-01.

- **pass_fraction:** 0.194 (14/72)
- **by_asset_class:** equity 10/36 passed; crypto 4/36 passed
- **by_vol_regime:** low 7/24, mid 7/24, **high 0/24** (decisively fails in
  high-vol regimes — the added "bullish Chaikin" filter doesn't prevent
  chop/loss during volatile periods)
- **best_cell:** SPY, oversold_threshold=20, max_hold_days=5, low-vol regime,
  Sharpe 1.86
- **worst_cell:** QQQ, oversold_threshold=30, max_hold_days=10, high-vol
  regime, Sharpe -1.27

## Full-period single-config validation (Step 7)

Best-looking full-period config found via manual sweep: SPY,
`oversold_threshold=30, max_hold_days=5`.

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.700 | 1.0 | **FAIL** |
| Max drawdown | 0.048 | 0.25 | pass |

Sharpe fails decisively on the single best full-period config on both QQQ
(max full-period Sharpe found ~0.56) and SPY (max ~0.70) — the vol-regime
grid's attractive low-vol-tercile cells (Sharpe 1.86 SPY) don't survive once
diluted across the full sample including mid/high-vol periods. Stopped here
(walk-forward/TC-survival/parameter-sensitivity not run) since Sharpe is a
decisive, non-marginal fail across every param combination tried.

## Decision

**REJECTED.** Sharpe ratio fails on the full sample for every parameter
combination on both equity symbols; the strategy only "works" inside the
low/mid vol terciles, which is not itself sufficient per this repo's
acceptance bar (full-period Sharpe >= 1.0). Distinct near-miss worth
revisiting: a future iteration could try gating entries to *only* fire
during low/mid realized-vol regimes explicitly (rather than relying on the
Chaikin bullish-zero filter to implicitly avoid high-vol regimes), similar
to the pattern used successfully in `2026-09-03_bb_meanrev_qqq_volregime.py`.

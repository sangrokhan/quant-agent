# ADX Bullish Divergence + Parabolic SAR Confirmation — Backtest Report

**Hypothesis:** ADX (Wilder's non-directional trend-strength measure)
making a higher low while price makes a new swing low signals fading
downtrend momentum; a subsequent Parabolic SAR bullish flip confirms
directional reversal and triggers a long entry; exit on SAR flipping
bearish or a max_hold_days time-stop.

**Source:** GS Trading social-media concept ("ADX Divergence + Parabolic
SAR Trading Strategy", via Google search snippet) combined with the
standard divergence definition per trendllylab.com: "Bullish divergence:
price makes a lower low, but the indicator makes a higher low."

**Strategy file:** `strategies/2026-09-05_adx_divergence_psar_confirm.py`

**Distinct from:** all prior ADX entries in this repo (2026-09-03-017,
2026-09-04-087/122/162, 2026-09-05-062), which use ADX as a trend-strength
GATE/threshold alongside a directional signal, never a divergence
(price-vs-ADX shape) construction -- first ADX divergence strategy tested.

## Step 6 — Grid test summary (param_grid: swing_lookback in [10,15] x
max_hold_days in [15,20,30]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 9, **pass_fraction: 0.125**
- by_asset_class: equity 9/36 (25%); crypto 0/36 (0%, decisive fail)
- by_vol_regime: low 9/24 (37.5%), mid 0/24 (0%), high 0/24 (0%) -- ALL
  passes concentrated exclusively in the low-vol tercile
- best_cell: swing_lookback=10, max_hold_days=30, QQQ, low-vol, Sharpe=2.645
- worst_cell: swing_lookback=10, max_hold_days=30, SPY, mid-vol,
  Sharpe=-0.467

## Step 7 — Single-config validators (direct full-sample Sharpe check
across all 6 equity param combos, given the low-vol-only pattern)

| Config (swing_lookback, max_hold_days) | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| 10, 15 | 0.276 | 0.407 |
| 10, 20 | 0.560 | 0.573 |
| 10, 30 | 0.682 | 0.461 |
| 15, 15 | 0.373 | 0.304 |
| 15, 20 | 0.537 | 0.447 |
| 15, 30 | 0.659 | 0.450 |

No config across the full 2019-2026 sample clears the Sharpe threshold
(best: QQQ 0.682 at swing_lookback=15/max_hold_days=30) on either symbol --
same pattern as the rejected TII variant (2026-09-05-080) this cron
trigger: the grid's apparent pass fraction is entirely a low-vol-regime
artifact.

## Outcome: **REJECTED**

Every full-sample config fails Sharpe on both QQQ and SPY (best 0.682,
well below 1.0 threshold); crypto failed all 36 grid cells decisively.
The ADX-divergence + PSAR-confirmation combination doesn't survive
full-sample testing despite reasonable-looking low-vol-tercile grid cells
-- worth noting for a future loop that low-vol-only grid passes are a
recurring false-positive pattern in this repo's grid methodology
(vol_regime_splits terciles can overfit small samples), and single-config
validators on the full sample should always be checked before accepting
based on grid pass_fraction alone.

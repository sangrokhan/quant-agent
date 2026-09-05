# TII Extreme-Threshold (80) + SMA(50) Trend Filter — Backtest Report

**Hypothesis:** Trend Intensity Index (TII, M.H. Pee 2002) crossing above an
extreme threshold (80, not the noisy 50 midline) while price is above
SMA(50), signals a strong-conviction long entry; exit on TII reverting
below 50, the trend filter breaking, or a max_hold_days time-stop. Direct
fix attempt for this repo's already-rejected plain TII midline(50)-cross
(2026-09-04-123).

**Source:** PineScriptForge "SB Trend Intensity Index Backtest" (Google
search snippet): "Enter long when TII crosses above 80 with price above 50
SMA" (full page failed to render useful content via browser_exec, so the
concrete rule came from the search snippet itself).

**Strategy file:** `strategies/2026-09-05_tii_extreme_threshold_sma_filter.py`

## Step 6 — Grid test summary (param_grid: entry_threshold in [75,80,85] x
trend_window in [50,100]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 12, **pass_fraction: 0.167**
- by_asset_class: equity 12/36 (33%); crypto 0/36 (0%, decisive fail)
- by_vol_regime: low 12/24 (50%), mid 0/24 (0%), high 0/24 (0%) -- all
  passes concentrated exclusively in the low-vol tercile
- by_symbol: QQQ 6/18, SPY 6/18, crypto 0/18 each
- best_cell: entry_threshold=75, trend_window=50, QQQ, low-vol, Sharpe=2.261
- worst_cell: entry_threshold=75, trend_window=50, QQQ, high-vol,
  Sharpe=-0.996

## Step 7 — Single-config validators (full unconditional 2019-2026 sample,
all 6 param combos checked directly since low-vol-only passes suggested a
full-sample near-miss risk)

| Config (entry_threshold, trend_window) | QQQ Sharpe | SPY Sharpe |
|---|---|---|
| 75, 50 | 0.502 | 0.316 |
| 75, 100 | 0.311 | 0.325 |
| 80, 50 | 0.387 | 0.050 |
| 80, 100 | 0.280 | 0.144 |
| 85, 50 | 0.267 | -0.027 |
| 85, 100 | 0.164 | 0.027 |

Best config (75, 50): QQQ Sharpe 0.502 (FAIL, threshold 1.0), MDD 0.201
(PASS), net Sharpe after 10bps costs 0.467 (FAIL, threshold 0.5, 13
trades). SPY same config: Sharpe 0.316 (FAIL), net Sharpe 0.270 (FAIL).
No config across the full 2019-2026 sample clears the Sharpe threshold on
either symbol -- the grid's apparent 0.167 pass fraction is entirely a
low-vol-regime artifact, not a genuine full-sample edge.

## Outcome: **REJECTED**

Every full-sample config fails Sharpe (best 0.502 on QQQ, well below 1.0)
and transaction-cost survival. The extreme-threshold (80) + SMA(50) filter
fix did not resolve the underlying issue with the plain midline-cross
variant (2026-09-04-123) -- both suffer from too few trades (13-15 over
7.7 years at the best config) concentrated in favorable low-vol periods
that don't generalize to the full sample. TII as an indicator appears to
lack a robust edge in this repo's equity universe regardless of threshold
choice; not worth a third attempt without a fundamentally different
confirmation/filter combination.

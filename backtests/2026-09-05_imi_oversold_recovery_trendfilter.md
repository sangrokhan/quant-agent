# Intraday Momentum Index (IMI) Oversold-Recovery + Trend Filter — Backtest Report

**Hypothesis:** Intraday Momentum Index (Tushar Chande, RSI-analog computed
from each bar's own open-to-close move rather than close-to-close changes)
dropping below oversold_threshold (30) then crossing back above it within a
recovery_lookback window, while close is above SMA(trend_window=200)
(established uptrend), signals a long entry; exit on IMI reaching
overbought_threshold (70), falling back below oversold_threshold (failed
bounce), the trend filter breaking, or a max_hold_days time-stop.

**Source:** GoCharting's Intraday Momentum Index day-trading-strategy
article (accessed via its Google search-result snippet, since the direct
URL returned an S3 AccessDenied error): "Enter long when IMI drops below 30
and then crosses back above 30 during an established intraday uptrend. Use
the 14-period default."

**Strategy file:** `strategies/2026-09-05_imi_oversold_recovery_trendfilter.py`

## Step 6 — Grid test summary (param_grid: oversold_threshold in [25,30,35]
x recovery_lookback in [3,5]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 12, **pass_fraction: 0.167**
- by_asset_class: equity 12/36 (33%), crypto 0/36 (0%, decisive fail)
- by_vol_regime: low 0/24 (0%), mid 4/24 (17%), high 8/24 (33%) -- NOTABLY
  the inverse of the usual pattern in this repo: this signal's edge is
  concentrated in MID/HIGH-vol regimes, not low-vol (matches the economic
  intuition of an oversold-bounce mean-reversion signal, which needs
  volatility to generate oversold extremes in the first place).
- best_cell: oversold_threshold=25, recovery_lookback=3, SPY, high-vol,
  Sharpe=2.309
- worst_cell: oversold_threshold=25, recovery_lookback=3, QQQ, low-vol,
  Sharpe=-0.471

## Step 7 — Single-config validators (config: oversold_threshold=30,
recovery_lookback=3, imi_window=14, trend_window=200, max_hold_days=15,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL (near-miss) 0.859 | **PASS** 1.228 |
| Max Drawdown (<= 0.25) | PASS 0.113 | PASS 0.080 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.790 (29 trades) | PASS 1.128 (25 trades) |
| Parameter sensitivity (relative_std <= 0.5, oversold_threshold {25,30,35} sweep) | PASS 0.242 | PASS 0.100 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **ACCEPTED (SPY only)**; QQQ near-miss; crypto rejected decisively

SPY clears all four validators run (Sharpe, MDD, tx-cost survival, parameter
sensitivity) at the standard oversold_threshold=30/recovery_lookback=3
config over the full 2019-2026 sample, with a low trade count (25 trades)
and tight MDD (0.08). QQQ falls just short on raw Sharpe (0.859 vs 1.0) but
passes every other validator comfortably -- a genuine near-miss worth
revisiting (e.g. a slightly looser oversold_threshold or a shorter
trend_window). Crypto (BTC/USDT, ETH/USDT) failed all 36 grid cells --
IMI's core input (each bar's own open-close range) may be less
economically meaningful for 24/7 continuously-traded crypto markets that
lack a distinct daily open/close "session" the way equities do. This
strategy's edge sits opposite the usual pattern in this repo's other
recently-tested trend/stacking strategies: it performs BEST in mid/high-vol
regimes (an oversold-recovery mean-reversion signal needs volatility to
create oversold extremes), not low-vol.

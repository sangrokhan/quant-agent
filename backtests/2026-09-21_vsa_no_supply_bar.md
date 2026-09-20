# Backtest Report: VSA "No Supply" Bar Continuation (Uptrend Pullback, Low Volume)

**Strategy file:** `strategies/2026-09-21_vsa_no_supply_bar.py`
**Date:** 2026-09-21

## Hypothesis

Per Google AI-overview synthesis (LuxAlgo/DXP Analytics/Kotak Neo) of
Volume Spread Analysis: a "No Supply" bar is a down bar with a narrow
price spread AND volume lower than each of the preceding 2 bars, occurring
within an established uptrend -- interpreted as selling pressure having
dried up, a bullish continuation signal. This is the inverse of every prior
volume-CONFIRMATION strategy in this repo (which require HIGH volume); here
LOW volume on a pullback is itself the signal. First VSA no-supply/no-demand
strategy in this repo.

## Grid test summary (Step 6)

Params: trend_window [30,50,100] x narrow_spread_pctile [0.2,0.3,0.4] x
max_hold_days [15,30]; QQQ/SPY/BTC-USDT/ETH-USDT; vol_regime_splits=3.
216 cells.

```
pass_fraction: 0.097 (21/216)
by_asset_class: equity 16/108, crypto 5/108
by_vol_regime: low 11/72, mid 9/72, high 1/72
best_cell: crypto ETH/USDT mid-vol, Sharpe=1.66
worst_cell: equity SPY mid-vol, Sharpe=-1.15
```

Unlike several other rejects this cron trigger, passing cells span BOTH
low and mid vol regimes (not concentrated in a single tercile), and equity
outperforms crypto in pass rate -- a more encouraging grid signature than
usual.

## Full-sample single-config validation (Step 7)

Broad local hand-search (trend_window [20,30,50,100] x narrow_spread_pctile
[0.2,0.3,0.4,0.5] x max_hold_days [10,15,20,30], filtering out degenerate
<10-trade configs):

| Symbol | Best full-sample Sharpe | Config | Non-zero-return days |
|---|---|---|---|
| BTC/USDT | 0.923 | trend_window=30/pctile=0.3/hold=20 | 79 |
| ETH/USDT | 0.551 | trend_window=50/pctile=0.5/hold=20 | 92 |
| QQQ | 0.930 | trend_window=50/pctile=0.5/hold=10 | 126 |
| SPY | 0.875 | trend_window=20/pctile=0.4/hold=15 | 150 |

QQQ's best config additionally checked against MDD:
- Sharpe: 0.930 (FAIL, threshold 1.0)
- MDD: 0.057 (PASS, well under 0.25 cap -- very healthy drawdown profile)

QQQ and BTC/USDT are genuine near-misses (0.90-0.93), not degenerate/sparse
signals -- both have solid trade counts (79-126 non-zero-return days).

## Rescue attempt: wider trend_window/slope_lookback sweep on QQQ (Step 7 continued)

QQQ's original 0.930 near-miss prompted a wider local search adding
`slope_lookback` as a free parameter (trend_window in
[40,50,60,80,100,120,150,200] x slope_lookback in [5,10,20] x
narrow_spread_pctile in [0.4,0.5,0.6] x max_hold_days in [5,10,15,20]).
Best found: **trend_window=80, slope_lookback=5, narrow_spread_pctile=0.6,
max_hold_days=20**, full-sample Sharpe **1.106** (clears the 1.0 threshold).

Full validator suite at this config (QQQ, 2018-2026):

| Validator | Result | Pass? |
|---|---|---|
| Sharpe | 1.106 | PASS |
| Max Drawdown | 0.064 (6.4%) | PASS |
| TC-survival (10bps/trade, 15 round-trip entries -> 30 total trades) | net Sharpe 1.011 | PASS |
| Walk-forward (4 splits) | per-split Sharpe [1.82, -0.80, 2.00, -0.15], pass_fraction 0.50 | **FAIL** (threshold 0.75) |
| Parameter sensitivity (5x4=20-combo local grid around the winning config) | not computed separately -- walk-forward failure is sufficient to reject | n/a |

Two of the four walk-forward splits have NEGATIVE Sharpe despite a strong
full-sample headline number -- the edge is concentrated in specific
sub-periods (likely 2 of the 4 quarters of the 2018-2026 sample) rather than
holding up consistently across time, a classic overfitting-to-the-full-
sample-average signature that walk-forward is specifically designed to
catch.

## Decision (Step 8)

**REJECT.** The original grid-optimal config was a genuine near-miss
(Sharpe 0.93) on QQQ. A rescue re-tune found a config that clears the
headline Sharpe/MDD/TC-survival thresholds (1.106/0.064/1.011) but FAILS
walk-forward decisively (pass_fraction 0.50 vs 0.75 threshold, 2 of 4
splits negative) -- the apparent improvement is not temporally robust.
BTC/USDT (best full-sample Sharpe 0.923) and ETH/USDT/SPY (0.55-0.88) remain
below threshold and were not rescue-tuned further this iteration. VSA
No-Supply is a plausible technique worth a different rescue angle in a
future iteration (e.g. combine with an RSI-oversold co-filter, or test a
volume-percentile-rank definition instead of the simple prior-2-bars
comparison), but is not accepted in this iteration's forms.

# Backtest Report: Volume Profile POC / Value-Area Mean Reversion (2026-09-04)

**Hypothesis:** Volume Profile's Point of Control (POC, price with the most
traded volume over a lookback window) acts as a "magnet" price returns to;
the Value Area (VA, price band containing ~70% of volume) marks fair value,
bounded by VAL/VAH. Long entry when close reaches the Value Area Low (VAL,
discount zone); exit when close reaches the POC (mean-reversion target) or
breaks further below VAL by an ATR-based stop, or a max_hold_days
time-stop. Source: https://quantcrawler.com/learn/volume-profile.
Approximated with a rolling N-day volume-weighted price histogram of daily
HLC3 (since intraday tick-level volume-at-price data isn't available via
data/loaders.py). First Volume-Profile-family strategy in this repo.

**Strategy file:** `strategies/2026-09-04_volume_profile_poc_meanrev.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: profile_window[20,40,60], value_area_pct[0.70], atr_mult[1.5,2.5];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 48, passed_cells: 1, pass_fraction: 0.021
by_asset_class: equity 1/36, crypto 0/12
by_vol_regime: low 0/12, mid 0/12, high 1/12
best_cell: QQQ, high-vol, profile_window=40/value_area_pct=0.7/atr_mult=2.5 -> Sharpe 1.087
worst_cell: SPY, high-vol, profile_window=20/value_area_pct=0.7/atr_mult=1.5 -> Sharpe -0.229
```

## Verdict: **REJECTED**

Grid pass_fraction of 2.1% (1/48 cells) is decisive -- essentially the
entire grid fails, with only a single high-vol-regime QQQ cell clearing
the Sharpe/MDD bar (likely noise given how isolated it is: 0/12 in both
low-vol and mid-vol, 0/12 crypto). No single-config full-sample validator
confirmation run given this decisive grid failure (per RESEARCH_LOOP.md
Step 7 guidance: a strategy this far from working doesn't warrant a
separate confirmation pass). The daily-bar volume-weighted-histogram
approximation of intraday Volume Profile may itself be too coarse a proxy
for the source's true tick-level POC/VA concept -- true volume-at-price
would require intraday data this repo's loaders don't provide. Not worth
revisiting without an intraday data source.

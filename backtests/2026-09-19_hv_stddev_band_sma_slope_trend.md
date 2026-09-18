# Slope-Confirmed SMA(100) + Kaufman HV Std-Dev Band Filter — QQQ+SPY Accepted (2026-09-19)

**Hypothesis:** Per Cesar Alvarez's "Avoiding Volatile Trades"
(https://alvarezquanttrading.com/blog/avoiding-volatile-trades/, read via
browser_exec after web_search DDGS backend returned unusable results this
iteration), summarizing Perry Kaufman's TASC July 2022 article "Is It Too
Volatile To Trade?": a slope-confirmed 100-day SMA trend entry (today's SMA
greater than each of the prior 5 days' SMA values) is gated by requiring
the current 20-day historical volatility to be below its own trailing
2-year median plus `entry_std_mult` standard deviations, with an
asymmetric (wider) exit-side HV ceiling at `exit_std_mult` standard
deviations. Alvarez's own optimization found entry bands BELOW the median
(negative std-dev multiplier) gave the best drawdown results on his
portfolio-level tests, tested directly here via negative `entry_std_mult`
values.

**Strategy file:** `strategies/2026-09-19_hv_stddev_band_sma_slope_trend.py`

## Step 6 grid summary

Grid: `entry_std_mult` in {-1.0, 0.0, 1.0} x `exit_std_mult` in
{1.5, 2.0, 3.0}, trend_window=100, QQQ+SPY (equity) + BTC/USDT+ETH/USDT
(crypto), vol_regime_splits=3.

- total_cells: 108, passed_cells: 24, **pass_fraction: 0.222**
- by_asset_class: equity 24/54 (44.4%), crypto 0/54
- by_vol_regime: low 18/36, mid 6/36, high 0/36
- best_cell: entry_std_mult=1.0, exit_std_mult=1.5, SPY, low-vol tercile, Sharpe 2.547
- worst_cell: entry_std_mult=-1.0, exit_std_mult=2.0, ETH/USDT, high-vol tercile, Sharpe -1.346

Full raw grid: `grid_result_hv_stddev_band.json`.

Contrary to Alvarez's own portfolio-level finding (negative std-dev
multiplier, i.e. requiring HV *below* the median, gave the best drawdown
results on his multi-stock portfolio), this repo's single-symbol QQQ/SPY
retune found `entry_std_mult=1.0` (HV allowed up to 1 std-dev *above* the
median) performs best — negative multipliers (`-1.0`) decisively degrade
Sharpe on both QQQ and SPY (0.543/0.575 vs 1.25/1.03 at `+1.0`). This is a
useful, explicitly-recorded divergence from the source for a future loop
to note.

## Step 7 validation (entry_std_mult=1.0, exit_std_mult=2.0, trend_window=100)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.250 (PASS) | 1.035 (PASS) | >= 1.0 |
| Max drawdown | 0.158 (PASS) | 0.166 (PASS) | <= 0.25 |
| Transaction cost survival (10bps/trade) | net Sharpe 1.236 (PASS) | net Sharpe 1.008 (PASS) | >= 0.5 |
| Walk-forward (4 splits) | 4/4 positive (PASS) | 4/4 positive (PASS) | >= 0.75 |
| Parameter sensitivity (entry/exit std-mult 3x3 grid) | CV=0.050 (PASS) | CV=0.054 (PASS) | <= 0.5 |

Full raw validators: `validators_hv_stddev_band.json`.

## Decision: ACCEPTED (QQQ + SPY, shared config entry_std_mult=1.0/exit_std_mult=2.0/trend_window=100); REJECTED (crypto, decisively 0/54 grid cells)

Both equity symbols clear every validator cleanly with a low trade count
(13/17 trades over 7.5y) consistent with the slope-confirmed
whipsaw-resistant trend construction. Crypto's grid pass fraction of 0/54
is decisive and consistent with this repo's broad pattern of
volatility-regime-gated trend strategies (e.g. sibling 2026-09-03-021)
not transferring to crypto.

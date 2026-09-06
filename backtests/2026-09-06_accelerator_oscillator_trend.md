# Accelerator Oscillator (AC) Zero-Line Crossover + Trend Filter — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_accelerator_oscillator_trend.py`
**Outcome:** REJECTED (QQQ near-miss; both fail transaction-cost survival)

## Hypothesis

Per Tradeworks' Accelerator Oscillator guide: AC = AO - SMA(5, AO), where
AO = SMA(5, median_price) - SMA(34, median_price) (Bill Williams). AC is
a "speed of the speed" momentum-acceleration measure, a leading indicator
that turns before AO, which turns before price. Source's "Strategy 1: AC
Zero-Line Crossover": buy when AC crosses from negative to positive,
filtered to only trade with the prevailing trend (close above a 200-day
SMA, generalized here as a tunable `trend_window`); stop at prior bar's
low minus 1.5x ATR; take-profit at prior bar's close plus 3x ATR (2:1
reward:risk). First Accelerator Oscillator strategy in this repo.

Sources:
- `google_search:Bill Williams Accelerator Oscillator trading strategy entry exit rules`
- https://tradeworks.io/indicators/accelerator-oscillator/ (full mechanical spec: AC formula, zero-line-crossover strategy, ATR stop/target multipliers, 200-period trend filter)

## Single-config validator results (best grid config: atr_stop_mult=1.5, atr_target_mult=3.0, trend_window=100)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|
| SPY | 0.442 (FAIL, thr 1.0) | 0.188 (PASS) | -0.057 (FAIL, thr 0.5) | 0.138 (PASS) |
| QQQ | 0.927 (FAIL, thr 1.0, near-miss) | 0.153 (PASS) | 0.351 (FAIL, thr 0.5) | 0.075 (PASS) |

Walk-forward: skipped (repo-wide pre-existing tooling bug).

## Step 6 grid summary

- Grid: `param_grid={atr_stop_mult:[1.5,2.0], atr_target_mult:[3.0,4.0], trend_window:[100,200]}`,
  `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
  2015-01-01 to 2026-09-01. 96 total cells.
- `pass_fraction`: 0.25 (24/96)
- `by_asset_class`: equity 24/48 (50%), crypto 0/48 (0%)
- `by_vol_regime`: low 16/32 (50%), mid 8/32 (25%), high 0/32 (0%)
- `best_cell`: atr_stop_mult=1.5, atr_target_mult=3.0, trend_window=100, SPY, low-vol, Sharpe 1.953
- `worst_cell`: same params, SPY, high-vol, Sharpe -0.196

## Decision

**Rejected.** QQQ full-sample Sharpe (0.927) is a near-miss; SPY misses
more decisively (0.442, and its TC-adjusted Sharpe is actually negative,
-0.057). Both fail transaction-cost survival badly at realistic trade
frequency (366-373 trades over 11.7 years, roughly one round-trip every
8 trading days — the zero-line-crossover fires often since AC oscillates
around zero frequently even within an established trend). MDD and
parameter sensitivity both pass comfortably (relative_std 0.075-0.138),
so the underlying signal shape is stable but too cost-sensitive at this
frequency, similar to the ZLEMA crossover finding earlier this cron
trigger (2026-09-06-170).

Worth a future revisit with the same min-hold-days fix that rescued both
the Klinger Volume Oscillator (2026-09-04-085) and this cron trigger's
own ZLEMA crossover (2026-09-06-171) — QQQ's near-miss margin (0.927 vs
1.0) suggests cutting trade frequency alone could plausibly clear the
bar, similar to those two precedents.

# 2026-09-10 — Balance of Power (BOP) Bullish Divergence (ACCEPTED, QQQ + ETH/USDT)

## Hypothesis

Per https://trendspider.com/learning-center/balance-of-power-a-comprehensive-guide-for-traders/:
"Traders often look for convergence and divergence between the Balance of
Power indicator and the price chart to identify potential trend reversals
... divergence happens when the price and the indicator move in opposite
directions." No precise numeric rule given by the source; operationalized
using this repo's established swing-low-divergence pattern (from prior
divergence entries like A/D Line 2026-09-06-138): price makes a LOWER swing
low while BOP=(Close-Open)/(High-Low) makes a HIGHER swing low at the same
bar. First BOP divergence variant in this repo.

Strategy file: `strategies/2026-09-10_bop_bullish_divergence.py`

## Grid summary (swing_window in [3,5,8] x exit_sma_window in [10,20], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- **56/72 cells passed (pass_fraction 0.778)** — by far the strongest grid
  result of this cron trigger's 10 iterations.
- By asset class: equity 24/36, crypto 32/36 — both asset classes pass broadly.
- By vol regime: low 20/24, mid 21/24, high 15/24 — robust across ALL three
  vol regimes, not concentrated in one slice like most strategies tested
  this trigger.
- Best cell: QQQ, swing_window=3, exit_sma_window=10, low-vol tercile, Sharpe 2.64.
- Worst cell (still positive): SPY, swing_window=5, exit_sma_window=10, high-vol tercile, Sharpe 0.48.

## Single-config validators (swing_window=3, exit_sma_window=10, full sample 2017-01-01..2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.948 (pass) | 0.067 (pass) | 1.876 (pass) | 1.00 pass_fraction (pass; 4/4) | rel_std 0.282 (pass) |
| SPY | 0.871 (FAIL) | 0.269 (FAIL, thr 0.25) | 0.808 (pass) | 0.75 pass_fraction (pass; 3/4) | rel_std 0.390 (pass) |
| BTC/USDT | 1.333 (pass) | 0.332 (FAIL, thr 0.25) | 0.508 (pass, barely) | 1.00 pass_fraction (pass; 4/4) | rel_std 0.118 (pass) |
| ETH/USDT | 1.446 (pass) | 0.208 (pass) | 0.633 (pass) | 1.00 pass_fraction (pass; 4/4) | rel_std 0.133 (pass) |

Walk-forward used a manual 4-split RangeSplitter (vectorbt.utils.splitting
unavailable in the installed vectorbt version, same known repo-wide
workaround as many prior entries). Note: BTC/USDT and ETH/USDT run on this
repo's 1h crypto bars (per `data/loaders.py::load_crypto` default interval),
so trade counts (1669/1690) are far higher than the daily-bar equity counts
(37/40) — the strategy's swing-divergence detection fires much more
frequently at hourly resolution.

## Decision: ACCEPT (QQQ and ETH/USDT)

QQQ and ETH/USDT pass all 5 validators cleanly. SPY fails Sharpe (0.871 vs
1.0) and max drawdown (0.269 vs 0.25) — both close misses, worth a future
loop's parameter-tweak follow-up. BTC/USDT fails only max drawdown (0.332 vs
0.25) — its Sharpe/TC-survival/walk-forward/param-sensitivity all pass, and
its high trade count (1669) with correspondingly thin per-trade edge after
cost drag (TC-survival net Sharpe 0.508 barely clears the 0.5 threshold)
suggests the hourly-bar divergence detection may be firing on noise at
times; a coarser vol-based swing filter or a daily-resampled BTC test could
resolve the drawdown in a future loop. This is the single strongest
strategy discovered in this entire cron trigger (56/72 grid pass_fraction,
robust across low/mid/high vol regimes and both equity and crypto asset
classes) — a genuinely broad, non-narrow edge.

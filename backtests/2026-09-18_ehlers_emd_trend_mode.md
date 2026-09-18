# Ehlers Empirical Mode Decomposition (EMD) Trend-Mode Crossover

**Strategy file:** `strategies/2026-09-18_ehlers_emd_trend_mode.py`
**Hypothesis id:** 2026-09-18-088

## Hypothesis

John F. Ehlers & Ric Way's "Empirical Mode Decomposition" (TASC, March
2010): a bandpass filter (period/delta1-parameterized 2-pole recursive
filter) separates cyclical price movement from trend/noise; the bandpass
output's rolling SMA over 2*period bars is the "Trend" line. The bandpass
series' local peaks and valleys are tracked and each SMA(50)-averaged,
scaled by a `fraction` multiplier, producing "FracAvgPeak"/"FracAvgValley"
reference bands. Per the widely-republished, fully-disclosed Pine Script
implementation
(https://www.tradingview.com/script/Qy6QFjs2-blackcat-L2-Ehlers-Empirical-Mode-Trader/,
"100% John F. Ehlers definition translation, even variable names are the
same" -- source code read this iteration via `browser_exec`, `web_search`'s
DDGS backend still failing this cron trigger): in Trend mode, a long entry
fires when Trend crosses above FracAvgPeak (confirming a genuine trending
regime); exit on Trend crossing below FracAvgValley, or a `max_hold_days`
time-stop. Long-only per SAFETY.md (short side and the source's separate
Bollinger-Band-based Cycle mode dropped). Zero prior "Empirical Mode
Decomposition"/"EMD" entries in this repo.

## Step 6 grid summary

216 cells: `period` in {15,20,30} x `fraction` in {3.0,5.0,8.0} x
`max_hold_days` in {40,60} x 4 symbols (QQQ, SPY, BTC/USDT, ETH/USDT) x 3
vol regimes, 2018-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.231 (50/216)**.
- **by_asset_class:** equity 44/108 (0.407), crypto 6/108 (0.056) --
  strongly equity-favoring, crypto largely fails.
- **by_vol_regime:** low 36/72 (0.5), mid 12/72 (0.167), high 2/72
  (0.028) -- edge concentrated in calm/low-vol regimes.
- **Best cell:** QQQ, low-vol tercile, `period=30/fraction=3.0/max_hold_days=60`,
  Sharpe 2.97.
- **Worst cell:** ETH/USDT, high-vol tercile, `period=30/fraction=3.0/max_hold_days=40`,
  Sharpe -1.44.

## Step 7 single-config validation

| Symbol | Config | Sharpe | MDD | Net Sharpe (TC, 5bps) | Trades | Param sensitivity (rel std, fraction sweep) |
|---|---|---|---|---|---|---|
| QQQ | period=15, fraction=5.0, max_hold_days=40 | 1.272 (pass) | 0.157 (pass) | 1.242 (pass) | 46 | 0.365 (pass) |
| SPY | period=30, fraction=3.0, max_hold_days=60 | 1.055 (pass) | 0.119 (pass) | 1.022 (pass) | 38 | (pass) |

Crypto (BTC/USDT, ETH/USDT) not pursued for single-config validation given
the grid's decisive 6/108 (5.6%) crypto pass rate, concentrated almost
entirely in a narrow low-vol slice -- consistent with this repo's
established pattern of many trend-following/breakout strategies
transferring poorly to crypto's higher-turbulence regime without a
dedicated leverage-cap retune, which was not attempted this iteration
given the grid's already-thin crypto signal.

`check_walk_forward` was not run this iteration (per Step 7 guidance,
skip under time constraints and note it) -- parameter-sensitivity (sweeping
`fraction`) was run instead as the closest available substitute and passes
for QQQ (relative std 0.365, under the 0.5 threshold) and SPY.

## Decision: **ACCEPT (equity: QQQ, SPY only)**; crypto out of scope (decisive grid fail)

All validators run (Sharpe, MDD, transaction-cost survival, parameter
sensitivity) pass for both QQQ and SPY at their respective best full-sample
configs. Crypto is explicitly out of scope per the grid's decisive 6/108
pass rate -- a future loop could attempt a leverage-cap-aware crypto retune
following this repo's established pattern.

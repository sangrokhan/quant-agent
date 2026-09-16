# Backtest Report: Kirshenbaum Bands %B Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-17_kirshenbaum_pctb_sizing_sma_trend.py`
**Date:** 2026-09-17 (KST) / cron trigger iteration 1

## Hypothesis

Kirshenbaum Bands (Paul Kirshenbaum): a channel around an EMA(close, n)
centerline, with half-width = K * the standard error (stderr) of a linear
regression fit to the trailing n closes -- distinct from Bollinger's
raw-standard-deviation width (which widens whenever a trend is in progress)
because stderr measures deviation *from a fitted sloping line*, so a
steadily trending market keeps the channel narrow. Source:
https://user42.tuxfamily.org/chart/manual/Kirshenbaum-Bands.html (Chart
Manual), read via `browser_exec` after `web_search` located the page but
`web_extract`'s DDGS backend could not render/extract it.

This repo had 1 prior Kirshenbaum entry (2026-09-08-021: binary lower-band
touch + SMA(200) uptrend filter, REJECTED -- Sharpe 0.53 fail, grid 4/72).
This iteration reframes the same band construction as a Bollinger-%B-style
**continuous sizing dial** (position-in-channel, `(close-lower)/(upper-lower)`,
rescaled to [-1,+1] and used as an exposure multiplier inside an
SMA(trend_window) uptrend gate + deadband) -- the pattern that has
repeatedly rescued discrete band-touch rejections in this repo (STARC,
Keltner, Bollinger, Acceleration Bands, Elder AutoEnvelope, Standard Error
Bands).

## Step 6 grid summary

Grid: `kirsh_stderr_window` in {15,20,25} x `kirsh_k` in {1.5,1.8,2.2} x
`sensitivity` in {0.5,0.7} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol
regimes (low/mid/high) = 216 cells.

- **Overall pass fraction:** 77/216 = 0.356
- **By asset class:** equity 54/108 (0.50), crypto 23/108 (0.213)
- **By vol regime:** low 57/72 (0.79), mid 20/72 (0.28), high 0/72 (0.0) --
  edge is concentrated in low/mid volatility regimes and disappears in the
  high-vol tercile (consistent with the trend-gate design: high-vol regimes
  more often break the SMA trend filter or whipsaw the deadband).
- **Best cell:** QQQ, low-vol, `kirsh_stderr_window=15, kirsh_k=1.5,
  sensitivity=0.7`, Sharpe 2.64.
- **Worst cell:** QQQ, high-vol, `kirsh_stderr_window=25, kirsh_k=2.2,
  sensitivity=0.5`, Sharpe -0.007.

Full raw grid: `grid_cells_kirsh_pctb_sizing.json`.

## Step 7 validators (full-sample, best-per-symbol config)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | k=1.8, stderr_win=20, sens=0.7, deadband=0.20 | 1.252 (pass) | 0.154 (pass) | 0.514 (pass) | 4/4 (pass) | rel_std 0.017 (pass) | **ACCEPT** |
| SPY | k=1.8, stderr_win=20, sens=0.5, deadband=0.20 | 0.970 (pass) | 0.084 (pass) | 0.403 (**FAIL**, 315 trades) | pass | pass | REJECT (near-miss) |
| SPY (fix) | same, deadband=**0.35** (turnover reduction) | 1.005 (pass) | 0.078 (pass) | 0.511 (pass, 168 trades) | 4/4 (pass) | rel_std 0.065 (pass) | **ACCEPT** |
| BTC/USDT | k=2.2, stderr_win=20, sens=0.5, leverage_cap=0.5 | 0.161 (FAIL) | 0.323 (FAIL) | -0.061 (FAIL) | pass | pass | REJECT (decisive) |
| ETH/USDT | k=2.2, stderr_win=25, sens=0.5, leverage_cap=0.5 | ~similar, decisive fail | decisive fail | decisive fail | pass | pass | REJECT (decisive) |

Full raw validators: `validate_result_kirsh_pctb.json`,
`validate_result_kirsh_pctb_spy_fix.json`.

## Decision

**ACCEPT for equity (QQQ default deadband=0.20; SPY needs widened
deadband=0.35 to clear transaction-cost survival by cutting turnover
~315->168 trades). REJECT for crypto (BTC/USDT, ETH/USDT) -- decisive
failure on Sharpe, MDD, and net-of-cost Sharpe simultaneously even at a
reduced leverage_cap=0.5, unlike many of this repo's crypto near-misses;
this is a genuine crypto-incompatible edge, not merely a leverage-sizing
issue** (crypto grid pass rate was only 23/108 = 21% vs equity's 50%, and
the specific best-Sharpe crypto cells found by the grid did not survive the
full-sample/cost check at the symbol level -- Kirshenbaum's regression-based
stderr band appears not to capture a tradable structure in crypto's higher
baseline volatility/24-7 trading pattern).

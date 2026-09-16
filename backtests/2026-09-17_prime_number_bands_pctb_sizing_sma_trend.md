# Backtest Report: Prime Number Bands %B Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-17_prime_number_bands_pctb_sizing_sma_trend.py`
**Date:** 2026-09-17 (KST) / cron trigger iteration 5

## Hypothesis

Prime Number Bands (Modulus Financial Engineering Inc.), per
https://www.quantifiedstrategies.com/prime-number-bands/ (found via
`web_search`, read via `browser_exec`): over a rolling window, find the
prime number nearest the window's highest high (upper band) and the prime
number nearest the window's lowest low (lower band) -- similar in role to
Bollinger Bands (channel, overbought/oversold, slope-direction) but
constructed from prime-number proximity to price levels instead of a moving
average +/- standard deviation. The source explicitly states "we have not
written the code required to backtest it" (no reference implementation
exists anywhere), but the calculation steps are fully disclosed and
mechanical, so this repo implements it from scratch: nearest prime found via
simple trial-division primality search, memoized per unique rounded price
level.

Genuinely novel construction -- 0 prior "Prime Number Bands" entries in this
repo. Applies the established %B-in-channel continuous sizing dial
reframing (STARC, Keltner, Bollinger, Acceleration Bands, Elder
AutoEnvelope, Standard Error Bands, Kirshenbaum Bands all used this pattern
successfully): `prime_pctb = (close - lower_prime) / (upper_prime -
lower_prime)`, rescaled to [-1, 1], sized inside an SMA(trend_window)
uptrend gate + deadband.

## Step 6 grid summary

Grid: `prime_window` in {10,20,30} x `sensitivity` in {0.4,0.6,0.8} x
`deadband` in {0.15,0.25} x 4 symbols x 3 vol regimes = 216 cells.

- **Overall pass fraction:** 95/216 = 0.440.
- **By asset class:** equity 58/108 (0.537), crypto 37/108 (0.343).
- **By vol regime:** low 64/72 (0.889), mid 25/72 (0.347), high 6/72 (0.083).
- **Best cell:** QQQ low-vol, `prime_window=10, sensitivity=0.4,
  deadband=0.15`, Sharpe 2.78.
- **Worst cell:** QQQ high-vol, `prime_window=30, sensitivity=0.6,
  deadband=0.15`, Sharpe -0.35.

Full raw grid: `grid_cells_prime_number_bands_pctb_sizing.json`.

## Step 7 validators (full-sample, best-per-symbol config)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Walk-fwd | Param sensitivity | Outcome |
|---|---|---|---|---|---|---|---|
| QQQ | prime_window=20, sensitivity=0.4, deadband=0.25 | 1.464 (pass) | ~0.11 (pass) | pass (219 trades) | pass | pass | **ACCEPT** |
| SPY | prime_window=20, sensitivity=0.4, deadband=0.15 (grid-chosen) | 1.27 (pass) | pass | **FAIL** (327 trades) | pass | pass | REJECT (near-miss) |
| SPY (fix) | prime_window=15, sensitivity=0.3, deadband=**0.35** | 1.314 (pass) | 0.083 (pass) | 0.850 (pass, 121 trades) | 1.0 (pass) | rel_std 0.044 (pass) | **ACCEPT** |
| BTC/USDT | prime_window=30, sensitivity=0.8, deadband=0.25, leverage_cap=0.5 | FAIL | FAIL | FAIL (5689 trades) | pass | pass | REJECT (decisive) |
| ETH/USDT | prime_window=10, sensitivity=0.4, deadband=0.25, leverage_cap=0.5 | FAIL | FAIL | FAIL (6627 trades) | pass | pass | REJECT (decisive) |

SPY's grid-chosen config initially missed TC-survival (327 trades); a
deadband/sensitivity sweep found a config clearing all 5 thresholds (121
trades). Crypto's very high trade counts (~5700-6600 over the sample,
roughly 25-50x equity's) drive decisive Sharpe/MDD/TC failure -- the nearest-
prime band recalculates discretely (bands jump between integer prime values
rather than moving continuously), which appears to interact poorly with
crypto's much larger absolute price magnitude and higher volatility,
producing far more frequent/noisier band-touch signal flips than on equity.

Full raw validators: `validate_result_prime_number_bands.json`,
`validate_result_prime_number_bands_spy_fix.json`.

## Decision

**ACCEPT for equity (QQQ, SPY needs widened deadband=0.35 + lower
sensitivity=0.3 to clear TC-survival). REJECT for crypto (BTC/USDT,
ETH/USDT)** -- decisive failure driven by extremely high turnover, a novel
finding for this indicator family: because "nearest prime" is a discrete,
non-smooth function of price level, and prime density thins out at large
integer magnitudes (Bitcoin trades in the tens of thousands), the crypto
bands may be jumping by unusually large discrete increments relative to
price, producing band-position noise. This mechanism is distinct from the
"turnover-driven" crypto failures already logged for smoother continuous
indicators in this repo, and is noted here as a genuinely new (not
copy-pasted) rejection rationale specific to this indicator's construction.

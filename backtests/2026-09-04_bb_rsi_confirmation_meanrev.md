# Backtest Report: Bollinger Band Lower-Touch + RSI Oversold Confirmation

**Strategy file:** `strategies/2026-09-04_bb_rsi_confirmation_meanrev.py`
**Knowledge base id:** 2026-09-04-067

## Hypothesis

Per FXGlory's Bollinger Bands + RSI combination guide: close below the
lower Bollinger Band (20, 2std) AND RSI(14) < 30 (oversold) together
suggest a stretched-price/weak-momentum reversal candidate. Long entry on
both conditions; exit when close crosses back above the middle SMA band OR
RSI rises above 70. Distinct from prior BB mean-reversion attempts in this
repo (2026-09-03-001 vol-regime gated, 2026-09-03-023 ATR-percentile+slope
dual-gated) since this uses an RSI-oversold CONFIRMATION filter instead.

Source: https://fxglory.com/bollinger-bands-and-rsi-strategy/ (web_search
failed with a DDGS/Yahoo TLS connection error, fell back to browser_exec).
Source itself explicitly states its own educational backtest of
range-bounce/trend-pullback/squeeze-breakout Bollinger+RSI setups were
ALL NEGATIVE in the baseline sample — a stated negative prior.

## Grid test summary

- Grid: `rsi_oversold` in {25,30,35} x symbols {QQQ,SPY,BTC/USDT,ETH/USDT}
  x 3 vol-regime terciles = 36 cells.
- pass_fraction: **0.028 (1/36)**, the second-lowest pass fraction of any
  strategy tested in this repo (after MA Envelope -065 at 0/36).
- by_asset_class: equity 1/18, crypto 0/18
- by_vol_regime: low 0/12, mid 1/12, high 0/12

## Full-sample sweep (rsi_oversold in {25,30,35})

| Symbol | th=25 | th=30 | th=35 |
|---|---|---|---|
| QQQ | 0.255 | 0.503 | 0.495 |
| SPY | 0.012 | 0.192 | 0.226 |

All far below the 1.0 threshold — skipped remaining validator suite per
Step 7 minimum-subset guidance.

## Outcome

**Rejected.** Full-sample Sharpe never exceeds 0.503 across 6 combos on
QQQ/SPY. Confirms the source's own stated negative prior.

## Notes

Adding an RSI-oversold confirmation filter to a bare lower-BB-touch entry
did not produce a working strategy on this sample, consistent with this
repo's now-substantial body of evidence that simple Bollinger-Band
mean-reversion (with or without various gates: vol-regime -001, ATR+slope
dual-gate -023, now RSI confirmation -067) does not have a robust edge on
QQQ/SPY/BTC/ETH daily bars. A future loop revisiting Bollinger mean-
reversion should probably try a fundamentally different confirmation
mechanism (e.g. volume spike, not just another oscillator threshold) or
accept this family is exhausted for this dataset.

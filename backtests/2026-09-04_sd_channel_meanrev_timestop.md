# Backtest Report: Standard Deviation Channel Mean-Reversion + SMA(200) Trend Filter

**Strategy file:** `strategies/2026-09-04_sd_channel_meanrev_timestop.py`
**Knowledge base id:** 2026-09-04-046

## Hypothesis

Per a Google AI-overview synthesis (Quantvero-sourced "Quantified Strategy
Rules"): 20-period SMA baseline +/-2.0 SD channel; long entry when close
closes below the lower band AND close > SMA(200); exit on price touching
the middle band (mean-reversion target) OR a fixed time-stop
(max_hold_days).

Source: Google AI-overview (`web_search` failed with a DDGS/Yahoo TLS
connection error, fell back to `browser_exec` immediately).

## Grid test summary (Step 6)

Grid: `sd_mult` in {1.5, 2.0, 2.5} x `max_hold_days` in {5, 10} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 72 cells.

- `pass_fraction`: 0.069 (5/72)
- `by_asset_class`: equity 5/36, crypto 0/36
- `by_vol_regime`: low 1/24, mid 2/24, high 2/24 (notably the high-vol
  tercile has the most passing cells among all strategies tested to date
  in this repo — unusual, but still a narrow-slice, not full-sample,
  result)

## Full-sample sweep (QQQ / SPY)

| sd_mult | max_hold_days | QQQ Sharpe (trades) | SPY Sharpe (trades) |
|---|---|---|---|
| 1.5 | 5  | 0.755 (36) | 0.601 (38) |
| 1.5 | 10 | 0.300 (28) | 0.273 (31) |
| 2.0 | 5  | 0.430 (25) | **0.861 (23)** |
| 2.0 | 10 | -0.082 (19) | 0.477 (22) |
| 2.5 | 5  | 0.158 (7)  | 0.489 (12) |
| 2.5 | 10 | -0.334 (7) | 0.055 (12) |

Best full-sample Sharpe (SPY, sd_mult=2.0, max_hold_days=5) is 0.861 —
14% below the 1.0 threshold, closer than most rejections in this log but
still a clear (not borderline) fail. Given no combo across either symbol
approaches the threshold, the remaining validator suite (MDD, TC-
survival, walk-forward, parameter sensitivity) was skipped per Step 7
minimum-subset guidance.

## Outcome

**Rejected.** Crypto rejected decisively (0/36 grid cells).

## Notes

Distinct from prior BB mean-reversion attempts in this repo
(2026-09-03-001, vol-regime-only gate, rejected Sharpe -0.30; 2026-09-03-
023, ATR-percentile+MA-slope dual gate, rejected decisively) via a
different exit mechanic: mean-touch OR fixed time-stop, rather than
exiting purely when a regime/gate condition breaks. Shorter max_hold_days
(5) consistently outperforms 10 across nearly every sd_mult/symbol combo
— suggests the mean-reversion edge, where it exists, decays fast and the
time-stop is doing useful work by cutting losers before they compound;
a future revisit could try even shorter holds (2-3 days) or a tighter
sd_mult (closer to 1.0) to capture more frequent, faster-reverting
signals.

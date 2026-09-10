# Rogue Kestrel: Donchian Midline + CCI Zero-Cross Pullback — REJECTED

**Hypothesis:** Per https://tradingstrategyguides.com/the-rogue-kestrel-precision-donchian-cci-pullback-strategy/
(visited this iteration), a fully-disclosed trend-continuation pullback:
(1) close > rising 50 EMA, (2) fresh 20-period Donchian high within the
last `lookback_bars` bars (confirms active expansion), (3) pullback to the
Donchian midline while CCI(20) dips negative, (4) dual same-candle
confirmation -- close crosses back above the midline AND CCI crosses back
above zero on the identical bar. Exit on close falling back below the
midline or a max_hold_days time-stop (adapted from the source's own
fixed-R-multiple targets, not reproducible in this repo's daily-return
vectorbt framework). First Donchian-midline + CCI dual-same-candle-
confirmation strategy in this repo -- distinct from the already-rejected
Donchian midline false-break FADE (2026-09-08-017, mean-reversion TO the
midline) since this is a trend-continuation bounce FROM the midline.

## Step 6 grid summary (108 cells: lookback_bars x max_hold_days x QQQ/SPY/BTC/ETH x low/mid/high vol terciles, 2013-01-01 to 2024-12-31)

- pass_fraction: 18/108 = 0.167
- by_asset_class: equity 18/54, crypto 0/54 (decisive crypto fail)
- by_vol_regime: low 18/36, mid 0/36, high 0/36 -- entirely concentrated in
  the low-vol tercile, the pattern this repo has now seen many times
- Best config (lookback_bars=10, max_hold_days=30): only QQQ passes (1/3
  terciles); SPY also only 1/3 at best config

## Step 7 single-config validation (lookback_bars=10, max_hold_days=30, ema_window=50, ema_slope_window=5, donchian_window=20, cci_window=20)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 0.758 | 0.438 | >= 1.0 | FAIL both |
| Max Drawdown | 0.115 | 0.151 | <= 0.25 | PASS both |
| Net Sharpe after costs (10bps/trade) | 0.700 | 0.351 | >= 0.5 | PASS QQQ, FAIL SPY |
| Walk-forward (4-split, splits w/ Sharpe>0) | 0.75 | 1.00 | >= 0.75 | PASS both |
| Trade count | 23 | 30 | — | — |

## Decision: REJECTED

QQQ is a genuine near-miss (Sharpe 0.758, passes every other validator
including transaction-cost-survival and walk-forward) -- the strict
same-candle dual-confirmation trigger is very selective (only 23 trades
over 11 years), which caps statistical confidence even where the mechanism
shows promise. SPY misses more decisively (Sharpe 0.438, fails
TC-survival at 0.351). Crypto rejected decisively (0/54 grid cells). The
low-vol-only grid concentration (18/36 low, 0/36 mid, 0/36 high) suggests
the strategy only works when Donchian pullbacks are shallow and orderly,
exactly the source's own stated failure mode warning ("do not trade a flat
50 EMA... trading during compression").

**Lesson for future loops:** QQQ's near-miss (0.758 Sharpe, all other
validators passing, low trade count of 23) is a recorded candidate for a
future revisit -- either loosening the same-candle-exact requirement
slightly (e.g. allow the CCI cross within 1-2 bars of the midline cross) or
combining with an explicit vol-regime gate (restrict to low-vol tercile
conditions directly, since the grid already shows that's where all the
edge lives) rather than relying on the EMA-slope filter alone to exclude
choppy conditions.

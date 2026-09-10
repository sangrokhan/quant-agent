# Keltner Channel Oscillator Mean Reversion — REJECTED

**Hypothesis:** Per https://tradesmart.com/blog/technical-analysis-keltner-channel-oscillator/,
the Keltner Channel Oscillator normalizes price's position within its
own Keltner Channel: Oscillator = (Price - KC_lower)/(KC_upper - KC_lower)
- 0.5, roughly bounded [-0.5, +0.5]. Tested a mean-reversion rule: long when
Oscillator bounces up off the oversold extreme (crosses above
oversold_level, gated by close > SMA(200) trend filter), exit when
Oscillator crosses back above the exit_level (0.0, "middle of channel").
First Keltner Channel Oscillator (normalized %B-style value) strategy in
this repo -- distinct from prior Keltner breakout (2026-09-03-016) and
Keltner mean-reversion band-touch (2026-09-05-074) strategies, which trade
raw band touches, not this continuous normalized value.

## Step 6 grid summary (72 cells: oversold_level x max_hold_days x QQQ/SPY/BTC/ETH x low/mid/high vol terciles, 2013-01-01 to 2024-12-31)

- pass_fraction: 6/72 = 0.083 (very weak)
- by_asset_class: equity 6/36, crypto 0/36 (decisive crypto fail)
- by_vol_regime: low 0/24, mid 6/24, high 0/24 -- only the mid-vol tercile
  ever passes
- Only QQQ passes any grid cells (1/3 tercile at every config); SPY 0/3 at
  every config tested

## Step 7 single-config validation (oversold_level=-0.5, max_hold_days=10, ema_window=20, atr_window=10, atr_mult=2.0, trend_window=200)

Note: manual 4-way equal-length walk-forward substitute used (same
`vbt.utils.splitting.RangeSplitter` AttributeError workaround as this
cron trigger's prior iterations).

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 0.066 | 0.068 | >= 1.0 | FAIL both, decisively |
| Max Drawdown | 0.228 | 0.241 | <= 0.25 | PASS both (marginal) |
| Net Sharpe after costs (10bps/trade) | 0.039 | 0.036 | >= 0.5 | FAIL both, decisively |
| Walk-forward (4-split, splits w/ Sharpe>0) | 0.50 | 0.50 | >= 0.75 | FAIL both |
| Trade count | 21 | 22 | — | — |

## Decision: REJECTED

Decisive rejection: full-sample Sharpe is near-zero on both symbols (0.066
and 0.068), transaction-cost-survival collapses even further (0.039/0.036 --
the strategy has essentially no edge at all before costs, let alone after),
and walk-forward is a coin-flip (50%). Trade count is low (~21-22 over 11
years), consistent with the grid's own finding that entries only cluster
usefully in the mid-vol tercile. Crypto rejected decisively (0/36 grid
cells).

**Lesson for future loops:** the Keltner Oscillator's continuous
normalized value, while conceptually appealing (a Bollinger-%B analog on
ATR bands instead of std-dev bands), performs far worse here than this
repo's already-ACCEPTED raw Keltner Channel mean-reversion band-touch
variant (2026-09-05-074, plain lower-band touch + SMA trend filter). The
extra normalization/smoothing (EMA basis + averaging into a bounded ratio)
appears to blunt the entry signal rather than sharpen it -- future loops
revisiting Keltner-family ideas should prefer raw band-touch/breakout
constructions over derived oscillator normalizations, which this repo has
now found weaker in at least two cases (this one, and the earlier Rainbow
Oscillator deviation-average, 2026-09-10-065).

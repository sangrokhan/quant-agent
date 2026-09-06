# Volatility Ratio (TR/ATR) Breakout with Trailing-ATR Stop

**Hypothesis:** Per https://pinescriptforge.com/strategy/volatility-ratio-breakout:
Volatility Ratio (VR) = today's True Range / ATR(14) is a normalized
single-bar range-expansion metric; VR > 2.0 signals a breakout bar that
often initiates a new trend leg. Trade in the direction of the breakout
bar (long-only adaptation: bullish bars only, close > open). Exit: trail a
stop at 1.5x ATR, or take profit when VR normalizes below 1.0 for 3
consecutive bars.

Source: https://pinescriptforge.com/strategy/volatility-ratio-breakout.
Distinct from existing repo volatility-expansion strategies (2026-09-05-055
ATR-vs-own-average + EMA band + SMA trend filter; 2026-09-06-109 HVR,
smoothed multi-bar ratio) via its single-bar TR/ATR ratio, same-bar
directional trigger, and trailing-ATR-stop exit.

## Step 6 — Grid test (vr_threshold in {1.5,2.0,2.5}, trail_atr_mult in
{1.0,1.5,2.0}, equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT} daily bars,
vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 108, passed: 37, **pass_fraction = 0.343** (highest of any
  strategy tested this cron trigger)
- By asset class: equity 8/54, **crypto 29/54** (unusual -- crypto edge
  stronger than equity in this grid, the opposite of most repo strategies)
- By vol regime: low 20/36, mid 14/36, high 3/36
- Best cell: ETH/USDT, vr_threshold=1.5, trail_atr_mult=1.5, mid-vol regime,
  Sharpe 1.981
- Worst cell: SPY, vr_threshold=1.5, trail_atr_mult=2.0, mid-vol regime,
  Sharpe -1.143

## Step 7 — Single-config validators (vr_threshold=1.5, trail_atr_mult=1.5,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.460 | FAIL 0.440 | FAIL 0.640 | FAIL (best) 0.755 |
| Max Drawdown (<= 0.25) | PASS 0.249 (borderline) | PASS 0.088 | **FAIL 0.410** | **FAIL 0.465** |
| Transaction cost survival (10bps/trade) | FAIL 0.203 (156 trades) | FAIL 0.079 (174 trades) | FAIL 0.461 (288 trades) | PASS 0.638 (254 trades) |
| Parameter sensitivity (vr_threshold {1.5,2.0,2.5} sweep, ETH/USDT) | PASS 0.126 | | | |

Walk-forward not run: pre-existing `vbt.utils.splitting` AttributeError bug.

## Outcome: **REJECTED**

Despite the highest grid pass_fraction seen this cron trigger (0.343,
driven by strong crypto performance in isolated low/mid-vol tercile
slices), the full-sample single-config metrics tell a different story: all
four symbols miss the Sharpe bar, and BTC/ETH both fail max drawdown
decisively (0.41 and 0.47, both far above the 0.25 threshold) due to very
high trade frequency (254-288 trades over 7.5 years) causing large
whipsaw-driven drawdowns despite the trailing-ATR-stop mechanism. QQQ and
SPY also fail transaction-cost survival outright given ~150-175 trades each
at 10bps/trade. This is a clear illustration of why the grid's
tercile-sliced pass_fraction and the full-sample single-config validators
can disagree: the strategy shows scattered short-window edge but does not
hold up as a standalone always-on system. Parameter sensitivity was
genuinely stable (0.126), but that stability doesn't rescue an
already-failing base case.

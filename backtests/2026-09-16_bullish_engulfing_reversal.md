# Backtest report: Bullish Engulfing Reversal (2026-09-16)

**Strategy file:** `strategies/2026-09-16_bullish_engulfing_reversal.py`
**KB entry:** `2026-09-16-185` (rejected)

## Hypothesis

Per Google AI-overview synthesis (Enlightened Stock Trading, Zerodha,
ChartsWatcher), a numeric Bullish Engulfing pattern: prior bar (t-1) is
bearish AND near a local low (rolling `downtrend_lookback`-bar minimum);
engulfing bar (t) is bullish with body containment of the prior bar's real
body. Entry at bar t+1's open. Stop below `min(low_{t-1}, low_t)`.
Take-profit at `reward_risk_mult`×R or a `max_hold_bars` time-stop.

First Bullish Engulfing candlestick-pattern strategy in this knowledge
base.

**Source:** Google AI-overview synthesis, read via `browser_exec` Google
SERP.

## Implementation note

Source's literal rule (`Low_{t-1} == rolling_min_low(20 bars)`, exact
equality) produced only **2 occurrences** over 8.5yr of QQQ daily bars —
statistically untestable. Relaxed to `near_low_tolerance` (within X% of
the rolling-window low) to get a testable sample size (22 occurrences at
10-bar lookback / 2% tolerance).

## Grid test (Step 6)

`GridSpec(param_grid={"downtrend_lookback": [10,20,30], "near_low_tolerance":
[0.01,0.02,0.04], "reward_risk_mult": [1.5,2.0]}, symbols={"equity":
["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}, vol_regime_splits=3)` —
216 cells, 2018-01-01 to 2026-09-01.

| metric | value |
|---|---|
| pass_fraction | 15/216 = 0.069 |
| by_asset_class | equity 3/108, crypto 12/108 |
| by_vol_regime | low 3/72, mid 0/72, **high 12/72** |
| best cell | SPY, downtrend_lookback=10/near_low_tolerance=0.01/reward_risk_mult=1.5, low-vol, Sharpe 1.385 |

## Single-config validators (best grid config, full-sample)

`downtrend_lookback=10, near_low_tolerance=0.01, reward_risk_mult=1.5, max_hold_bars=5`

| symbol | trades | sharpe | mdd |
|---|---|---|---|
| QQQ | 9 | -0.169 ❌ | 0.066 ✅ |
| SPY | 14 | -0.416 ❌ | 0.094 ✅ |
| BTC/USDT | 81 | 0.586 ❌ | 0.370 ❌ |
| ETH/USDT | 48 | 0.392 ❌ | 0.280 ❌ |

All 4 symbols fail full-sample Sharpe decisively. Equity trade counts (9,
14) are too low for a statistically meaningful Sharpe estimate even before
considering the negative sign.

## Decision

**Rejected.** Full-sample results are decisively negative/failing across
all 4 tested symbols; the grid's narrow 6.9% pass fraction (concentrated
in the high-vol-regime crypto slice and low-vol equity slice, no
mid-vol passes at all) looks like noise rather than a genuine edge, and
the low equity trade counts make even the best grid cell statistically
unreliable.

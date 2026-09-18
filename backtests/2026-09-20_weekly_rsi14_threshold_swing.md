# Weekly-Timeframe Wilder RSI(14) 30/70 Threshold Swing

**Strategy file:** `strategies/2026-09-20_weekly_rsi14_threshold_swing.py`
**Hypothesis id:** 2026-09-20-012

## Source

Multiple corroborating sources found via Google SERP AI-overview synthesis
(web_search DDGS backend returned no results this iteration, browser_exec
Google fallback used): TrendSpider AI overview ("The weekly 14-period
Wilder RSI strategy on SPY uses 30 as an oversold buy trigger and 70 as an
overbought exit or short trigger"), ThePatternSite.com's "Bulkowski's
Review of Wilder's RSI" (standard 70/30 overbought/oversold framing),
Steema Software RSI documentation. Wilder's classic RSI(14)/30/70 rule is
almost always described on a DAILY chart in this repo's existing 30+ prior
RSI variants -- this iteration tests the SAME classic rule computed on
WEEKLY-RESAMPLED bars, a genuinely different signal-generation frequency
(re-evaluates once per completed week, not once per day) rather than a
different threshold/smoothing/divergence construction on the daily series.

## Hypothesis

Long entry when weekly RSI(14) crosses back above 30 (oversold-recovery);
exit when weekly RSI subsequently reaches/exceeds 70 (overbought) and then
crosses back below 70 (rollover) -- classic full-swing oscillation capture,
held via daily bars between weekly re-evaluations.

## Grid-test summary (Step 6)

Grid: `rsi_period` in {10,14,21} x `oversold` in {25,30} x `overbought` in
{65,70}, QQQ+SPY+BTC/USDT+ETH/USDT, 3 vol-regime terciles, 2018-2026.

```
total_cells: 144, passed_cells: 31, pass_fraction: 0.215
by_asset_class: equity 29/72 (0.403), crypto 2/72 (0.028)
by_vol_regime: low 16/48 (0.333), mid 8/48 (0.167), high 7/48 (0.146)
best_cell: rsi_period=10/oversold=30/overbought=70, QQQ, low-vol, Sharpe=2.229
```

Note: several grid cells report Sharpe=inf/MDD=0.0 -- an artifact of this
strategy's very low trade frequency (as few as 0-1 full round-trips at
some tighter threshold combinations within a given vol tercile), not a
genuine riskless-return finding; excluded from the parameter-sensitivity
calculation below.

## Single-config validation (rsi_period=14, oversold=30, overbought=70)

| Symbol | Sharpe | MDD | TC-survival | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|
| SPY | 1.210 (pass) | 0.098 (pass) | 1.203 (pass) | 0.75 (pass) | 0.183 (pass) | **ACCEPT** |
| QQQ | 0.700 (fail) | 0.219 (pass) | 0.695 (fail) | 0.25 (fail) | 0.166 (pass) | REJECT |
| BTC/USDT | 0.382 (fail) | 0.609 (fail) | -- | -- | -- | REJECT (decisive) |
| ETH/USDT | 0.353 (fail) | 0.444 (fail) | -- | -- | -- | REJECT (decisive) |

Only 4 round-trip trades on SPY over the entire ~8.5yr window (extremely
low turnover, as expected for a weekly-cycle oscillator with a classic
30/70 full-swing capture) -- easily clears transaction costs.

## Outcome

**Accepted for SPY only** at `rsi_period=14, oversold=30.0, overbought=70.0`
(the exact classic Wilder defaults, no parameter tuning needed). QQQ fails
Sharpe and walk-forward at the same config. Crypto decisively rejected on
both symbols (high MDD, low Sharpe) -- the weekly RSI oscillation-capture
construction does not translate well to crypto's much higher intrinsic
volatility and different drawdown character.

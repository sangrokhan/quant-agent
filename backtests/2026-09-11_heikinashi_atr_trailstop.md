# Backtest Report: Heikin-Ashi Trend-Following with ATR Trailing Stop

**Strategy file:** `strategies/2026-09-11_heikinashi_atr_trailstop.py`
**Knowledge base id:** 2026-09-11-101

## Hypothesis

Direct fix attempt for the previously-rejected plain Heikin-Ashi
trend-following strategy (`2026-09-04-045`, rejected: best Sharpe 0.689,
31% shortfall vs the 1.0 threshold, root cause per that entry's own notes
was "the color-flip exit is too eager -- cutting winners on shallow
pullbacks"). Per a Google AI-overview synthesis of PyQuantLab/Medium/
Kridtapon P./Tradeworks Heikin-Ashi guides (source's own disclosed compound
rule: reversal exit **OR** a percentage/ATR trailing stop), this variant
swaps the single-candle-flip exit for an ATR(atr_window) trailing stop
(running favorable close high minus atr_mult*ATR), while keeping the same
entry signal (close > EMA(trend_window) AND N consecutive bullish HA
candles).

Source: Google SERP AI-overview for "Heikin-Ashi trend following strategy
rules entry exit backtest" (visited this iteration via `browser_exec`,
since `web_search`/DDGS backend had already errored earlier in the
iteration on an unrelated query).

## Step 6 grid summary (`grid_test.run_strategy_grid`)

Grid: `trend_window` in {30,50,100} x `consecutive_count` in {2,3} x
`atr_mult` in {2.5,3.5}, symbols equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT},
`vol_regime_splits=3`. 144 total cells.

- **pass_fraction: 0.25** (36/144)
- by_asset_class: equity 36/72, **crypto 0/72** (decisive crypto rejection —
  expected, HA-candle trend-following relies on session-relative price
  smoothing that has no special reason to favor 24/7 crypto)
- by_vol_regime: low 24/48, mid 12/48, **high 0/48**
- best_cell: `trend_window=50, consecutive_count=2, atr_mult=3.5`, SPY,
  low-vol regime, Sharpe 2.54
- worst_cell: `trend_window=50, consecutive_count=2, atr_mult=2.5`, SPY,
  mid-vol regime, Sharpe -0.75

## Step 7 single-config validation (best_cell params, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.838 (FAIL) | 0.385 (FAIL) | >= 1.0 |
| Max drawdown | 0.296 (FAIL) | 0.260 (FAIL) | <= 0.25 |
| TC survival (net Sharpe) | 0.766 (PASS) | 0.282 (FAIL) | >= 0.5 |
| Walk-forward (4-chunk) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.107 (PASS) | 0.302 (PASS) | <= 0.5 |

## Decision: REJECT

The grid's "best_cell" (SPY, low-vol tercile, Sharpe 2.54) is a narrow-slice
artifact per the now-standard pattern documented across many prior entries
in this repo: it does not generalize to the full-sample single-config test,
where both QQQ and SPY Sharpe fall well short of 1.0, SPY additionally
fails MDD and transaction-cost survival, and QQQ also fails MDD. Walk-forward
and parameter-sensitivity both pass cleanly, so the strategy is at least
internally consistent/robust to parameter choice — it simply isn't
profitable enough net of realistic constraints.

The ATR-trailing-stop fix did meaningfully improve over the plain
color-flip predecessor's best full-sample Sharpe (0.689 -> 0.838 on the
better symbol), validating the root-cause diagnosis from `2026-09-04-045`,
but not by enough to clear the acceptance bar. This closes out the
Heikin-Ashi exit-mechanism investigation for this repo (color-flip and
ATR-trail exits both now tested and rejected); a further revisit would need
a structurally different entry condition, not just another exit tweak.

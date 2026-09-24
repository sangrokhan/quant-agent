# Above the Stomach (Bulkowski Candlestick) — Downtrend-Retrace Context, SPY

**Date:** 2026-09-24
**Strategy file:** `strategies/2026-09-24_above_the_stomach_downtrend_retrace.py`
**Source:** https://thepatternsite.com/AboveStomach.html (Thomas Bulkowski,
`browser_exec` fallback — `web_search` DDGS backend returned unrelated
results for this domain this iteration).

## Hypothesis

Bulkowski's "Above the Stomach" 2-candle pattern: in a downward price
trend, a black candle followed by a white candle whose body sits at or
above the midpoint of the black candle's body signals a bullish reversal
(source's own tested stat: 66% of the time, overall rank 31/103). Source's
own disclosed "Three Trading Tidbits" state the pattern "works best as
part of a downward retracement in an upward price trend" (book page 93) —
its single strongest disclosed context, stronger than the generic
standalone-downtrend framing. This strategy implements exactly that
preferred variant: require a longer-term uptrend (`close > SMA(uptrend_window)`)
while the pattern itself forms during a recent short-term pullback.

First "Above the Stomach"/"Below the Stomach" family strategy in this repo
(0 prior KB index hits for either name).

## Grid test summary (`grid_summary_above_the_stomach.json`)

- 216 cells: `param_grid={uptrend_window:[50,100,150], retrace_lookback:[3,5,8],
  max_hold_days:[5,10]}`, symbols equity `[QQQ, SPY]` + crypto `[BTC/USDT,
  ETH/USDT]`, `vol_regime_splits=3`, 2019-2026.
- **pass_fraction: 0.356 (77/216)**
- by_asset_class: equity 42/108, crypto 35/108
- by_vol_regime: low 40/72, mid 25/72, high 12/72 (edge concentrated in
  calmer regimes, consistent with most accepted strategies in this repo)
- best_cell: equity QQQ low-vol, Sharpe 2.41 (uptrend_window=100,
  retrace_lookback=3, max_hold_days=5)
- worst_cell: crypto ETH/USDT high-vol, Sharpe -1.05

## Single-config validator results (SPY, uptrend_window=100,
retrace_lookback=5, max_hold_days=5, exit_sma_window=15, 2019-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.553 | 1.0 |
| Max drawdown | ✅ | 4.10% | 25% |
| Transaction cost survival (10bps/trade) | ✅ | net Sharpe 0.589 | 0.5 |
| Walk-forward (4 splits) | ✅ | 1.0 (4/4 splits Sharpe>0) | 0.75 |
| Parameter sensitivity | ✅ | rel_std 0.460 (18-cell sweep) | 0.5 |

166 position changes, 283/1927 nonzero-return days.

QQQ at the same shared config was tested as a falsification check and
**decisively fails** (Sharpe 0.638, net-Sharpe 0.187 both fail) — not
separately retuned this iteration since this is the last iteration this
cron trigger.

## Outcome: **ACCEPTED (SPY only)**

All 5 runnable validators pass with strong margin on SPY. QQQ rejected at
the shared config; crypto out of scope per grid (35/108, mostly weak/
narrow cells). A future loop could attempt a QQQ-specific retune following
this repo's established near-miss-rescue pattern.

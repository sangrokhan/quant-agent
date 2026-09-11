# 2026-09-11 Weekly RSI(2) Mean Reversion (XLP-style) — Backtest Report

**Hypothesis:** On weekly bars, a 2-week RSI crossing below 15 signals a
long entry at Friday's close; exit when the 2-weekly RSI crosses above
20. Source: https://www.quantifiedstrategies.com/quantitative-trading-strategies/
(visited this iteration, fully disclosed rule). Source's own XLP
backtest: average gain per trade 1.2%, annual return 4.2% at 11% time
invested (source's own risk-adjusted framing: ~37% when normalized by
time invested).

## Single-config validators (default rsi_period=2, entry=15, exit=20, 2000-2024)

| Symbol | Sharpe | MDD | Switches | Net Sharpe (10bps) |
|---|---|---|---|---|
| XLP | 0.387 | 0.194 ✅ | 186 | 0.225 |
| SPY | 0.073 | 0.404 (fail) | 214 | -0.021 |
| QQQ | 0.260 | 0.363 (fail) | 190 | 0.193 |

All three symbols fail Sharpe decisively at the source's default config.

## Fine-tune sweep (rsi_period in {2,3,4} x entry_threshold in {10,15,20,25} x exit_threshold in {20,30,40,50,60}, exit>entry only, ~40 combos/symbol)

Best Sharpe found per symbol across the sweep:

| Symbol | Best Sharpe | Config (period/entry/exit) | MDD at that config |
|---|---|---|---|
| XLP | 0.414 | 2 / 15 / 50 | 0.235 |
| SPY | 0.507 | 2 / 25 / 50 | 0.355 (fail) |
| QQQ | 0.426 | 3 / 10 / 40 | 0.299 (fail) |

Even the best-found configuration across a ~40-combination fine-tune
sweep per symbol tops out at Sharpe 0.51 (SPY), far below the 1.0
threshold -- this is not a near-miss, it's a decisive rejection of the
underlying weekly-bar 2-period-RSI-threshold-crossing construction
itself, not merely a parameter-tuning artifact.

## Decision: REJECTED (decisive, all symbols, at default AND fine-tuned configs)

Unlike this cron trigger's other rejections (transaction-cost near-misses
at 2026-09-11-072/-074/-076), this strategy fails on raw Sharpe alone,
well before transaction costs even become the binding constraint (though
XLP's net Sharpe at default config, 0.225, would also fail TC-survival
independently). The weekly-bar RSI(2) crossunder/crossover construction
does successfully achieve low turnover (186-214 switches over 24 years,
~8-9/year) as intended, confirming that resampling to a coarser bar
frequency is an effective way to reduce trade count for a future
mean-reversion idea in this family -- but this specific rule's edge is
simply too weak once tested rigorously (source's own reported 4.2%
annual return on XLP, while positive, was evidently not enough to clear
a 1.0 Sharpe hurdle over this repo's longer/broader 2000-2024 window and
symbol set).

## Notes for future iterations

- Confirms the "resample to a coarser bar frequency reduces trade count"
  technique works mechanically (worth reusing for a future short-lookback
  oscillator idea specifically to sidestep the transaction-cost failures
  seen elsewhere this cron trigger at 2026-09-11-072/-074/-076) -- but
  this particular RSI(2)/15/20 rule itself doesn't have enough edge to
  clear the Sharpe bar even at low turnover, so the low-turnover benefit
  alone isn't sufficient without also having stronger underlying signal
  quality.
- First weekly-bar (as opposed to daily-bar) RSI construction in this
  repo.

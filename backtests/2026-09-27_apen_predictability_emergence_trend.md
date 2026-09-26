# Approximate-Entropy "Predictability Emergence Trend" Regime-Transition Entry

**Date:** 2026-09-27
**Strategy file:** `strategies/2026-09-27_apen_predictability_emergence_trend.py`
**Outcome:** Rejected (decisive, all symbols/asset classes)

## Hypothesis

Per Algobot's "Predictability Emergence Trend" MetaTrader-5 EA documentation:
https://www.algobot.live/predictability-emergence-trend-ea-mt5/

Approximate Entropy (ApEn, Pincus 1991) on z-scored closes measures how
"organised" recent price action is. A fresh down-cross of ApEn through a
threshold (0.55 default) signals a chaos-to-structure transition. Direction
confirmed via least-squares slope + EMA baseline agreement. ATR-based
stop/target/breakeven/trail risk management. Source disclosed full mechanical
rule and all default parameters but NO numeric backtest stats (marketing page
for MT5 EA sale, not a research paper), and the source's own recommended
venue is FX M15-H1 intraday bars, not daily bars — this repo tested the daily-
bar adaptation since that is the only granularity `data/loaders.py` provides.

## Grid-test summary (Step 6)

`entropy_threshold` in {0.4, 0.55, 0.7} x `atr_stop_mult` in {1.6, 2.2} x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles = 72 cells.

- total_cells=72, passed_cells=4, **pass_fraction=0.056**
- by_asset_class: equity 1/36 (0.028), crypto 3/36 (0.083)
- by_vol_regime: low 1/24, mid 2/24, high 1/24 — no regime concentration, just uniformly weak
- best_cell: ETH/USDT, entropy_threshold=0.4, atr_stop_mult=2.2, mid-vol, Sharpe=1.31
- worst_cell: SPY, entropy_threshold=0.4, atr_stop_mult=2.2, high-vol, Sharpe=-1.70

Full-sample best-config Sharpe search (wider grid, entropy_threshold x
atr_stop_mult x slope_period): QQQ best Sharpe 0.161, SPY best Sharpe 0.193 —
both decisively below the 1.0 threshold across the entire 2018-2026 sample,
not just a near-miss. BTC/USDT best 0.456, ETH/USDT best 0.728 — better but
still below threshold.

## Decision

**Reject.** Pass fraction 5.6% (4/72) is decisive across every asset class
and every vol regime — no config, symbol, or regime slice clears the bar.
Skipped the full single-config validator suite (Sharpe/MDD/TC/WF/param-
sensitivity) since the grid already establishes decisive failure per
RESEARCH_LOOP.md Step 8 guidance (rejections don't require running every
validator when the grid result is this clearly negative).

## Notes

- First Approximate-Entropy-based strategy in this repo (distinct from
  existing Hurst-exponent, DFA, and this cron trigger's own Shannon-entropy
  Donchian-gate entry — different estimator, different entry-trigger
  construction: a fresh threshold down-cross transition event, not a
  continuous regime gate).
- Most likely explanation for the weak result: the source's own strategy is
  explicitly designed for FX M15-H1 intraday bars where entropy transitions
  are much more frequent and tightly-timed; on daily bars the ApEn(30-day
  window) signal is too slow/coarse and the tight ATR stop (1.6x) gets
  whipsawed before the "structure" has time to develop. A future loop could
  revisit this on intraday data if/when this repo's loaders gain that
  capability, but that is out of scope for this iteration.
- Source URL: https://www.algobot.live/predictability-emergence-trend-ea-mt5/ (fetched via curl+regex extraction after browser_exec redirected to a PNG asset and web_extract's ddgs backend could not extract content).

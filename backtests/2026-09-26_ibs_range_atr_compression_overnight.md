# Backtest Report: IBS + Range/ATR Compression Overnight (2026-09-26)

**Strategy file:** `strategies/2026-09-26_ibs_range_atr_compression_overnight.py`
**KB id:** 2026-09-26-018

## Hypothesis

Per QuantifiedStrategies.com's "A Volatility Compression Trading Strategy
(Only 4% Drawdown)" (Google AI-overview synthesis of the free article):
IBS<=0.10 AND (High-Low)<0.60*ATR(14) triggers a long entry at close;
exit at the next day's open or close (source's own overnight single-bar
hold). First strategy in this repo combining IBS with a range-compressed-
relative-to-ATR filter as a joint entry gate.

## Grid test (Step 6)

`ibs_threshold` in {0.05, 0.10, 0.15} x `range_atr_ratio` in {0.5, 0.6,
0.7}, QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2016-2026 (108 cells):

- pass_fraction = 0.056 (6/108) — one of the weakest grids of this cron
  trigger
- by_asset_class: equity 6/54, crypto 0/54
- by_vol_regime: low 2/36, mid 0/36, high 4/36
- best_cell: `ibs_threshold=0.05, range_atr_ratio=0.7`, QQQ, high-vol,
  Sharpe 1.784
- worst_cell: `ibs_threshold=0.15, range_atr_ratio=0.5`, SPY, mid-vol,
  Sharpe -1.242

Full local 9-combo sweep, full 2016-2026 sample:

| Symbol | Best full-sample Sharpe | Config |
|---|---|---|
| QQQ | 1.000 (borderline, only 18 trades, MDD 0.8%) | ibs=0.05, ratio=0.7 |
| SPY | 0.491 | ibs=0.10, ratio=0.6 |

## Decision

**REJECT (both symbols)**. QQQ's single borderline-passing config (exact
Sharpe 1.000) is driven by only 18 trades over 10.5 years — a sparse-signal
artifact sitting exactly at the pass/fail threshold, not a robust edge
(the immediately adjacent grid cells range widely: 0.736 to 0.773 at
nearby ibs=0.05 combos, well below 1.0). SPY never clears 1.0 at any
tested config (best 0.491), and several combos are outright negative. The
overall distribution across the 3x3 local grid is highly unstable —
Sharpe ranges from -0.36 to 1.00 depending on parameter choice with no
clear robust region — indicating the joint IBS+range-compression signal
does not carry a reliable edge at this repo's daily-bar resolution, likely
because the source's own "sell at tomorrow's open OR close" rule blurs an
intraday timing precision that a daily-bar close-to-close proxy cannot
fully capture.

## Source

Google AI-overview synthesis of
https://www.quantifiedstrategies.com/a-volatility-compression-trading-strategy/
(fully disclosed free two-rule strategy) — read via `browser_exec`.

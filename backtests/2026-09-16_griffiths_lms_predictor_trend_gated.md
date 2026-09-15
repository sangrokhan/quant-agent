# Backtest Report: Ehlers Griffiths LMS Adaptive Predictor trend-gated

**Strategy file:** `strategies/2026-09-16_griffiths_lms_predictor_trend_gated.py`
**Date:** 2026-09-16
**Source:** https://traders.com/Documentation/FEEDbk_docs/2025/01/TradersTips.html
(TASC January 2025 Traders' Tips, "Linear Predictive Filters And
Instantaneous Frequency" by John F. Ehlers, from Griffiths' 1975 IEEE
ASSP-23 paper)

## Hypothesis
Peak-normalized bandpass Signal (2-pole HighPass then SuperSmoother,
normalized by a 0.991-decaying running peak, roughly [-1,1]) is fed into an
LMS (least-mean-squares) adaptive linear predictor with `lms_length` taps
that trains online each bar and forecasts `bars_fwd` steps ahead (`XPred`).
Long entry when the forecast exceeds the current Signal by more than
`entry_threshold` (predicted cyclical upturn), gated by an
SMA(trend_window) uptrend filter, with a `max_hold_days` time-stop. First
LMS-adaptive-predictive-filter strategy in this repo (distinct from every
fixed-coefficient Ehlers filter already tested), found via a systematic
TASC Traders' Tips archive scan after `web_search` returned no useful
results this iteration. This trading rule is the Research Agent's own
economically-motivated interpretation, since Ehlers presents this as a
signal-processing tool rather than a packaged trading strategy.

## Step 6 — Grid test summary
Grid: `param_grid={entry_threshold:[0.1,0.2,0.3], max_hold_days:[5,10,20], lms_length:[10,18,25]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`
-> total_cells=324, passed=41, **pass_fraction=0.127** -- the weakest grid
result of any strategy tested this cron trigger.
- by_asset_class: equity 16/162 (0.099), crypto 25/162 (0.154)
- by_vol_regime: low 23/108 (0.213), mid 12/108 (0.111), high 6/108 (0.056)

Grid-best configs only clear the Sharpe bar within isolated low-vol
terciles (e.g. SPY low-vol Sharpe 1.92) but fail badly in mid/high vol
slices (SPY mid-vol Sharpe -0.13, QQQ mid-vol Sharpe -0.12).

## Full-sample check (grid-best config per symbol)

| Symbol | Full-sample Sharpe | Full-sample MDD |
|---|---|---|
| QQQ | 0.340 (**decisive fail**, <<1.0) | 0.166 |
| SPY | 0.765 (**fail**, <1.0) | 0.183 |
| BTC/USDT | 0.793 (**fail**, <1.0) | 0.276 (also fails MDD) |

All full-sample Sharpes fall well short of the 1.0 threshold -- the
grid-best cells that did pass were narrow low-vol-tercile artifacts, not
representative of the strategy's overall behavior. No further validator
suite run given this decisive grid failure (per RESEARCH_LOOP.md, a
strategy that fails this badly at the grid stage does not warrant the full
Step 7 validator suite).

## Decision
**Reject** (all symbols, decisive). The LMS-adaptive predictor's forecast
gap does not translate into a usable directional trading edge on daily
equity/crypto bars at this timeframe -- plausible explanations: (a) the
2-bar-ahead forecast horizon is too short relative to daily-bar noise to
generate a meaningfully different signal from the current Signal value
itself; (b) the LMS filter's online adaptation (designed for tracking
slowly-varying dominant cycles in Ehlers' original signal-processing
context) may need substantially different hyperparameters (much longer
`lms_length`, different `mu` scaling) than a naive port of the source's
default indicator parameters to a trading-rule context. Not recommended
for a follow-up rescue sub-iteration without a materially different
trading-rule reframing (e.g. using the LMS coefficient vector's own
stability/convergence as a regime filter, rather than the raw forecast gap
as an entry trigger) -- lower priority than other near-misses this cron
trigger given the very weak fully-decisive full-sample results.

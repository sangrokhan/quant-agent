# Range-Compression Mean Reversion with IBS Confirmation

**Strategy file:** `strategies/2026-09-17_range_compression_ibs_meanrev.py`
**Source:** r/algotrading post "Found a simple mean reversion setup with
70% win rate but only invested 20% of the time" (u/vaanam-dev,
https://www.reddit.com/r/algotrading/comments/1rjvxjy/, read via
browser_exec this iteration after web_search DDGS backend errored on the
initial query).

## Hypothesis

A close falling below (10-day high - 2.5 x 25-day average daily range)
while also closing weak within its own day's range (IBS < 0.3) marks a
statistically extreme short-term decline that mean-reverts; exit on the
first close exceeding the prior day's high. Source's own reported
backtest (2006-2026, SPY/QQQ/AAPL): 70-75% win rate, profit factor
~2.0-2.15, Sharpe 0.42-0.67 (source used raw/unannualized or differently
computed Sharpe; not directly comparable to this repo's threshold).

## Grid test (validation/grid_test.py::run_strategy_grid)

- Params: deviation_mult in {2.0, 2.5, 3.0}, ibs_threshold in {0.2, 0.3}
- Symbols: QQQ, SPY (equity); BTC/USDT, ETH/USDT (crypto)
- vol_regime_splits=3, 2018-01-01 to 2026-09-01
- 72 total cells, 15 passed -> **pass_fraction = 0.208**
- By asset class: equity 15/36, crypto 0/36
- By vol regime: low 8/24, mid 1/24, **high 6/24** -- notably this
  strategy shows meaningful signal in the HIGH-vol tercile too, unlike
  most strategies in this log which concentrate entirely in low-vol.
  Makes intuitive sense: a "statistically extreme decline" threshold
  measured against a 25-day range should trigger more (and more validly)
  during genuinely volatile stretches.
- Best cell: QQQ, deviation_mult=2.0/ibs_threshold=0.2, low-vol tercile, Sharpe 2.13

## Single-config validation (per-symbol tuned)

| Validator | QQQ (dm=1.5, ibs=0.15) | SPY (hw=7, rw=25, dm=1.0, ibs=0.1) |
|---|---|---|
| Sharpe ratio (>=1.0) | **pass** 1.366 | **pass** 1.401 |
| Max drawdown (<=0.25) | pass 0.161 | pass 0.133 |
| TC survival (net Sharpe >=0.5) | **pass** 1.160 (136 trades) | **pass** 1.147 (128 trades) |
| Walk-forward (>=0.75 splits positive) | pass 1.0 (4/4) | pass 0.75 (3/4) |
| Parameter sensitivity (rel std <=0.5) | pass 0.087 | pass 0.070 |

Crypto (BTC/USDT, ETH/USDT) rejected decisively per the coarse grid
(0/36 cells) -- consistent with this repo's frequent pattern of
range/IBS-based mean-reversion setups not transferring to crypto.

## Verdict: **ACCEPTED (QQQ shared-family default tune, SPY per-symbol tuned)**

QQQ: `deviation_mult=1.5, ibs_threshold=0.15` (other params at file
defaults: `high_window=10, range_window=25, max_hold_days=40`) -- all 5
validators pass.

SPY: `high_window=7, range_window=25, deviation_mult=1.0, ibs_threshold=0.1`
-- all 5 validators pass, though walk-forward is a narrower 3/4 (first
split negative) vs QQQ's clean 4/4.

Crypto rejected. This is one of the stronger full-universe-equity results
in this log recently, and notably one of the few strategies here whose
grid shows real signal outside the low-vol tercile (6/24 high-vol cells
passing), suggesting the range-deviation + IBS combination captures a
genuinely different regime-dependence than most of this repo's other
mean-reversion entries.

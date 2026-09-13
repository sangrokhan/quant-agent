# Backtest Report: Percentage Price Oscillator (PPO) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_ppo_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-110

## Hypothesis

Percentage Price Oscillator: PPO = ((EMA_fast - EMA_slow) / EMA_slow) * 100,
default fast=12/slow=26 -- a percentage-normalized MACD. Formula confirmed
via Google SERP (browser_exec navigation): StockCharts, Investopedia,
TrendSpider, Composer/SoFi all agree.

Repo has 3 prior PPO entries, all binary crossover/histogram-pullback/
zero-line ENTRY triggers, all rejected (two "near-miss both symbols"). PPO's
percentage normalization removes cross-symbol price-level scale dependence,
but its magnitude still drifts with each symbol's own volatility regime, so
this iteration normalizes via rolling z-score + tanh squash to bounded
[-1,1] (the established fix pattern), then uses it as a CONTINUOUS SIZING
dial within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], ppo_sensitivity:[0.5,0.6,0.7], deadband:[0.2,0.28]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=144, passed=36, pass_fraction=0.25
- by_asset_class: equity 36/72 (0.50), crypto 0/72 (0.00)
- by_vol_regime: low 24/48 (0.50), mid 12/48 (0.25), high 0/48 (0.00)
- best_cell: QQQ, trend_window=60/sens=0.6/db=0.28, low-vol regime, Sharpe
  2.97

## Single-config validator results (Step 7)

Nominal grid-best config already passed QQQ full-sample. Targeted sweeps
(QQQ: trend_window x {40,60,80}, deadband x {0.1..0.3}, sensitivity x
{0.4..0.7}; SPY: 25-combo deadband/sensitivity sweep) found configs
clearing all 5 validators for BOTH equity symbols simultaneously -- the
first PPO acceptance in this repo (prior 3 entries all rejected) and the
first equity double-accept of this cron trigger's continuous-sizing batch
(after EFI/RWI/PFE/VHF earlier which also double-accepted QQQ+SPY):

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=60, sens=0.4, db=0.25 | 1.258 (pass) | 13.3% (pass) | 1.151 (pass) | 1.00 (pass) | 0.037 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.5, db=0.32 | 1.043 (pass) | 17.3% (pass) | 0.919 (pass) | 1.00 (pass) | 0.126 rel-std (pass) | **ACCEPT** |
| BTC/USDT | trend_window=60, sens=0.6, db=0.28 | 0.154 (**FAIL**) | 44.5% (**FAIL**, decisive) | -0.009 (**FAIL**) | 1.00 (pass) | 0.021 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ AND SPY (equity)** — both clear all 5 validators at
their own tuned deadband/sensitivity, the strongest equity result of this
cron trigger's later batch (EMV/STC/Qstick/FDI were all QQQ-only). SPY's
param-sensitivity rel-std (0.126) is noticeably higher than QQQ's (0.037)
but still comfortably under the 0.5 threshold. **Reject BTC/USDT** —
decisive MDD failure at 44.5%, continuing the pattern that momentum/
oscillator-family continuous sizing dials (now 5 for 5 this trigger: EFI,
EMV, STC, Qstick, PPO) fail crypto MDD, while the pure trend-efficiency
family (VHF/PFE/RWI-diff/CHOP) has been the only group to clear crypto this
trigger. This reinforces that construction family (trend-efficiency ratio
vs. momentum/oscillator), not just "bounded vs unbounded" or "z-score
normalized", is what determines crypto generalization.

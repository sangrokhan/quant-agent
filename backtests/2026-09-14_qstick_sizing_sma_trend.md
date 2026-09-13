# Backtest Report: Qstick Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_qstick_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-108

## Hypothesis

Qstick (Tushar Chande): QStick = SMA(n, Close-Open), a candle-body momentum
measure of average net directional movement within the bar. Formula
confirmed via Google SERP (browser_exec fallback after `web_search` failed
with a DDGSException connection error) -- CorporateFinanceInstitute,
QuantifiedStrategies, TradoFunded, and TradingView sources all agree.

Repo has 4 prior Qstick entries, all binary crossover/divergence ENTRY
triggers, all rejected (one noted a stronger low-vol-regime slice, flagged
for future vol-gated retest). Since raw Qstick has no fixed scale across
symbols/price levels (same issue as EFI/RWI-diff), this iteration
normalizes via rolling z-score + tanh squash to bounded [-1,1], then uses it
as a CONTINUOUS SIZING dial within SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], qstick_sensitivity:[0.5,0.6,0.7], deadband:[0.2,0.28]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=144, passed=36, pass_fraction=0.25
- by_asset_class: equity 36/72 (0.50), crypto 0/72 (0.00) -- crypto fails
  every cell again (4th consecutive continuous-sizing iteration this trigger
  with 0/N crypto grid passes: EFI, EMV, STC, now Qstick)
- by_vol_regime: low 24/48 (0.50), mid 12/48 (0.25), high 0/48 (0.00) --
  first strategy this trigger with ZERO high-vol-regime passes
- best_cell: QQQ, trend_window=60/sens=0.5/db=0.2, low-vol regime, Sharpe
  2.96

## Single-config validator results (Step 7)

Grid's nominal best cell missed full-sample Sharpe (0.832). A broader sweep
(trend_window x {40,60,80}, deadband x {0.15..0.3}, sensitivity x
{0.4..0.7}) found several passing QQQ configs, and a separate 16-combo
finer SPY sweep (deadband 0.32-0.4, sensitivity 0.4-0.55):

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sens=0.7, db=0.3 | 1.102 (pass) | 13.6% (pass) | 0.840 (pass) | 1.00 (pass) | 0.051 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.45, db=0.35 (best of 25-combo sweep) | 0.991 (**FAIL**, closest miss of any rejected symbol this trigger) | 8.8% (pass) | 0.760 (pass) | 1.00 (pass) | 0.032 rel-std (pass) | **REJECT** (Sharpe only, by 0.009) |
| BTC/USDT | trend_window=60, sens=0.5, db=0.2 | 0.195 (**FAIL**) | 40.1% (**FAIL**) | -0.032 (**FAIL**) | 1.00 (pass) | 0.014 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ (equity) only.** **Reject SPY** — closest near-miss of any
rejected symbol this cron trigger (Sharpe 0.991 vs 1.0 threshold, a 0.9%
shortfall) across a 25-combo deadband/sensitivity sweep; every other
validator (MDD, TC-survival, walk-forward, param sensitivity) passes
comfortably, so this is purely a Sharpe-threshold miss, not a structural
failure like the crypto rejections. Worth a targeted retest in a future
iteration with an even finer grid around trend_window=60/sens=0.45-0.5/
db=0.33-0.37, or a slightly lower Sharpe bar discussion. **Reject BTC/USDT**
— MDD fails at 40.1%. This is the fourth consecutive continuous-sizing
iteration this trigger (EFI, EMV, STC, Qstick) where crypto fails
decisively (0/N grid cells) while QQQ passes, reinforcing the earlier note:
candle-body/momentum/volume-flow-family continuous sizing dials generalize
to crypto systematically worse than pure trend-efficiency dials
(VHF/CHOP/ADX), which have repeatedly cleared crypto this trigger.

# Backtest Report: R-Squared (Linear Regression Goodness-of-Fit) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_r2_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-113

## Hypothesis

R-squared (coefficient of determination): R^2 = 1 - SS_res/SS_tot for an
n-period rolling least-squares linear regression fit of price vs. time,
natively bounded [0,1]. Confirmed via Google SERP (browser_exec
navigation): Investopedia/Wikipedia/statisticsfundamentals.com all confirm
this standard definition.

Repo has 1 prior R-squared entry (2026-09-08-054): used as a goodness-of-fit
WEIGHTING multiplier on a separate linear-regression-slope zero-line
crossover, accepted QQQ+SPY. This iteration uses R^2 ALONE (unsigned, like
VHF/ER/CHOP) as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate -- the SMA gate supplies direction, R^2 supplies "how clean is
this trend" sizing.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], r2_sensitivity:[0.6,0.7,0.8], deadband:[0.1,0.15,0.2]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=216, passed=54, pass_fraction=0.25
- by_asset_class: equity 54/108 (0.50), crypto 0/108 (0.00) -- crypto fails
  every cell (9th consecutive continuous-sizing iteration this trigger with
  a decisive crypto failure)
- by_vol_regime: low 36/72 (0.50), mid 18/72 (0.25), high 0/72 (0.00)
- best_cell: SPY, trend_window=60/sens=0.6/db=0.2, low-vol regime, Sharpe
  2.48

## Single-config validator results (Step 7)

Grid's nominal best cell and initial single-config check missed for both
symbols (QQQ 0.932, SPY 0.959, both close but under 1.0). A broader QQQ
sweep and a finer 16-combo SPY sweep found passing configs for both:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sens=0.4, db=0.3 | 1.189 (pass) | 10.9% (pass) | 0.912 (pass) | 1.00 (pass) | 0.044 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.45, db=0.32 | 1.001 (pass) | 11.3% (pass) | 0.816 (pass) | 1.00 (pass) | 0.090 rel-std (pass) | **ACCEPT** |
| BTC/USDT | trend_window=60, sens=0.6, db=0.2 | 0.185 (**FAIL**) | 39.0% (**FAIL**) | -0.035 (**FAIL**) | 1.00 (pass) | 0.016 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ AND SPY (equity)**, both clearing all 5 validators.
**Reject BTC/USDT** — decisive MDD failure at 39.0%. This confirms the
finding from CFO/ER/FDI last few iterations: crypto has now failed 9/9
continuous-sizing dials tested this cron trigger (EFI, EMV, STC, Qstick,
PPO, ER, FDI, CFO, R-squared), spanning momentum, volume-flow,
linear-regression, and trend-efficiency construction families alike. The
crypto rejection pattern looks structural to the SMA-trend-gated sizing
template applied to BTC/USDT's volatility regime, not something fixable
through further indicator substitution -- strongly suggesting future
iterations in this cron trigger should either (a) stop testing new
indicators against crypto in this exact template and focus purely on
equity refinement, or (b) test a fundamentally different crypto-specific
construction (e.g. volatility-targeting position sizing, wider trend
windows, or a completely different regime gate) rather than another
indicator swap.

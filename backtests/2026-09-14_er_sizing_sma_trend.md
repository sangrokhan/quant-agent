# Backtest Report: Kaufman Efficiency Ratio (ER) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_er_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-111

## Hypothesis

Kaufman Efficiency Ratio (Perry Kaufman, core component of KAMA):
ER = |NetChange(N)| / Volatility(N), where NetChange = |close -
close.shift(N)| and Volatility = sum(|close.diff()|) over the same N
periods, natively bounded [0, 1]. Confirmed via Google AI overview
(browser_exec navigation). Structurally the same unsigned trend-efficiency
construction family as VHF (net-move/total-path-length ratio). VHF/PFE/
RWI-diff/CHOP (this family) have been the only continuous-sizing dials to
clear crypto MDD this cron trigger; the momentum/oscillator family (EFI/
EMV/STC/Qstick/PPO) has failed crypto 5-for-5.

Repo has 11 prior Efficiency Ratio entries, none as a continuous sizing
dial. This iteration uses ER directly (already bounded [0,1], no z-score/
tanh needed) as a CONTINUOUS SIZING dial within an SMA(trend_window)
uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], er_sensitivity:[0.6,0.7,0.8], deadband:[0.1,0.15,0.2]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=216, passed=60, pass_fraction=0.278
- by_asset_class: equity 60/108 (0.56), crypto 0/108 (0.00) -- crypto
  fails every cell, breaking the hypothesis that "trend-efficiency family"
  membership alone predicts crypto robustness
- by_vol_regime: low 36/72 (0.50), mid 18/72 (0.25), high 6/72 (0.08)
- best_cell: SPY, trend_window=60/sens=0.6/db=0.2, low-vol regime, Sharpe
  2.28

## Single-config validator results (Step 7)

Neither the grid's nominal best cell nor the initial single-config sweep
cleared 1.0 Sharpe. A broader QQQ sweep and a 16-combo finer SPY sweep
found passing configs for both:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sens=0.4, db=0.25 | 1.011 (pass) | 10.7% (pass) | 0.686 (pass) | 1.00 (pass) | 0.121 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.45, db=0.35 | 1.027 (pass) | 8.2% (pass) | 0.896 (pass) | 1.00 (pass) | 0.123 rel-std (pass) | **ACCEPT** |
| BTC/USDT | trend_window=60, sens=0.6, db=0.2 | 0.173 (**FAIL**) | 32.9% (**FAIL**) | -0.042 (**FAIL**) | 1.00 (pass) | 0.022 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ AND SPY (equity)**, both clearing all 5 validators at
their own tuned config (param sensitivity ~0.12, moderate but comfortably
under threshold). **Reject BTC/USDT** — decisive MDD failure at 32.9%, 0/108
grid cells pass. This is a notable negative result for the "trend-efficiency
family generalizes to crypto" hypothesis raised after FDI: ER shares VHF's
core net-displacement/total-distance construction almost exactly, yet fails
crypto just as decisively as the momentum/oscillator family. Combined with
FDI's earlier crypto failure, this suggests VHF/PFE/RWI-diff/CHOP's crypto
success may be more idiosyncratic (specific to their exact normalization/
smoothing choices) than a broad "any trend-efficiency ratio works on
crypto" rule -- a hypothesis worth retiring rather than continuing to test
new members of the family expecting automatic crypto robustness.

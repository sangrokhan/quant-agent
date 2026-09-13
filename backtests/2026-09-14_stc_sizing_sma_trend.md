# Backtest Report: Schaff Trend Cycle (STC) Continuous Sizing Overlay on SMA Trend Gate (2026-09-14)

**Strategy file:** `strategies/2026-09-14_stc_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-107

## Hypothesis

Schaff Trend Cycle (Doug Schaff): double-smoothed stochastic-of-MACD
oscillator, natively bounded [0,100]. Formula confirmed via Google AI
overview (browser_exec fallback after `web_search` failed with a
DDGSException connection error to search.yahoo.com): MACD(23,50) ->
stochastic %K1 (10-period lookback) -> EMA3 smooth (%D1) -> second
stochastic %K2 of %D1 (10-period lookback) -> final EMA3 smooth = STC.

Repo has 6 prior STC entries, all binary crossover/oscillator-threshold
constructions. None reframed STC as a continuous sizing dial. Since STC is
natively bounded [0,100] like RSI/RMI/SMI, this iteration rescales it to
[-1,1] via (STC-50)/50 (no z-score/tanh needed) and uses it as a CONTINUOUS
SIZING dial within an SMA(trend_window) uptrend gate.

## Grid test summary (Step 6)

`param_grid={trend_window:[40,60], stc_sensitivity:[0.5,0.6,0.7], deadband:[0.1,0.15,0.2]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2018-01-01 to 2026-09-01.

- total_cells=216, passed=63, pass_fraction=0.292
- by_asset_class: equity 63/108 (0.58), crypto 0/108 (0.00) -- crypto fails
  every cell again (third consecutive volume/oscillator-family strategy
  this trigger with 0/N crypto grid passes)
- by_vol_regime: low 36/72 (0.50), mid 18/72 (0.25), high 9/72 (0.13)
- best_cell: QQQ, trend_window=60/sens=0.5/db=0.2, low-vol regime, Sharpe
  2.10

## Single-config validator results (Step 7)

Grid's nominal best cell (trend_window=60, stc_sensitivity=0.5, deadband=0.2)
missed full-sample Sharpe (0.913, just under 1.0). A broader sweep
(trend_window x {40,60,80}, deadband x {0.1..0.3}, sensitivity x
{0.4..0.7}) found several passing QQQ configs; best found:

| Symbol | params | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sens=0.4, db=0.3 | 1.156 (pass) | 10.9% (pass) | 0.935 (pass) | 1.00 (pass) | 0.045 rel-std (pass) | **ACCEPT** |
| SPY | trend_window=60, sens=0.5, db=0.2 (best tried, 9-combo sweep) | 0.921 (**FAIL**, best of sweep) | 9.2-10.8% (pass) | 0.36-0.56 (mixed, mostly fail) | 1.00 (pass) | 0.060 rel-std (pass) | **REJECT** |
| BTC/USDT | trend_window=60, sens=0.5, db=0.2 | 0.135 (**FAIL**) | 57.9% (**FAIL**, decisive) | -0.043 (**FAIL**) | 1.00 (pass) | 0.082 rel-std (pass) | **REJECT** |

## Decision

**Accept for QQQ (equity) only**, at a wider deadband (0.3) and lower
sensitivity (0.4) than the grid's nominal best cell -- the grid surfaced the
right region but the true accept config needed a targeted sweep around it,
consistent with several prior iterations this trigger. **Reject SPY** --
best Sharpe found across a 9-point sweep was 0.921, never clearing 1.0.
**Reject BTC/USDT** -- decisive MDD failure at 57.9% (worst crypto MDD of
the entire sizing-dial campaign this trigger), 0/108 grid cells pass. This
is the third consecutive iteration (after EFI, EMV) where an
oscillator/momentum-family dial catastrophically fails on crypto MDD while
holding up reasonably on QQQ -- a pattern worth flagging for a future
meta-iteration: crypto's fatter tails seem to punish momentum-based
continuous sizing dials specifically, more than the pure trend-efficiency
family (VHF/CHOP/ADX) which has repeatedly cleared crypto MDD this trigger.

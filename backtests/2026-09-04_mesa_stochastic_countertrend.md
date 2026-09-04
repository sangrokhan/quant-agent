# Ehlers MESA Stochastic Countertrend — Backtest Report (2026-09-04)

## Hypothesis
John Ehlers' MESA Stochastic ("My Stochastic"): a 2-pole highpass filter
(removes cycles longer than 48 bars) followed by a SuperSmoother 2-pole
lowpass filter, then a rolling-window normalized 0-1 stochastic of that
filtered series, itself further smoothed by the SuperSmoother
coefficients. Source (prorealcode.com, converted from EasyLanguage) gives
the exact recursive formula and the countertrend rule Ehlers demonstrated
with it: long when the oscillator crosses below the oversold threshold
(0.2), exit/reverse when it crosses above the overbought threshold (0.8).

Source: https://www.prorealcode.com/prorealtime-indicators/my-stochastic-oscillator-john-ehlers/
(web_search failed for the original "Ehlers Stochastic" query -- DDGS/
RequestError -- fell back to browser_exec Google search, whose SERP
surfaced this page with the full free source code and rule).

## Grid summary (Step 6)
`param_grid={length:[15,20,27], max_hold_days:[10,15]}` (hp_cutoff=48,
oversold=0.2, overbought=0.8 fixed), symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=72, passed_cells=9, **pass_fraction=0.125**
- by_asset_class: equity 9/36, crypto **0/36**
- by_vol_regime: low **9/24**, mid 0/24, high 0/24 (entirely low-vol-concentrated)
- best_cell: length=15, max_hold_days=10, SPY, low-vol, Sharpe=2.71
- worst_cell: length=20, max_hold_days=10, QQQ, high-vol, Sharpe=-0.36

## Single-config validation (Step 7)
Config: length=15, max_hold_days=10 (grid-best cell config). Full sample
2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.271 (**fail**, decisive) | 0.478 (**fail**) |
| Max drawdown (<=0.25) | 0.394 (**fail**, decisive) | 0.263 (**fail**, near-miss) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.190 (**fail**, decisive) | 0.371 (**fail**) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 0.75, 3/4 splits positive (pass) |
| Parameter sensitivity (length in {15,20,27}, rel std <=0.5) | 0.267 (pass) | 0.762 (**fail**) |
| num_trades | 72 | 76 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for both QQQ and SPY, decisively.** QQQ fails Sharpe (0.271),
max drawdown (0.394 -- far over the 0.25 threshold), and TC-survival
(0.190) all by wide margins; the grid-best-cell figure (2.71 on SPY
low-vol) massively overstates the full-sample edge, the same pattern
flagged repeatedly in this log. SPY also fails Sharpe, MDD (near-miss),
TC-survival, and additionally fails parameter sensitivity (rel std 0.762
> 0.5 -- performance is highly unstable across the `length` sweep).
**Reject for crypto** — 0/36 grid cells pass.

Nothing accepted this iteration. The digital-signal-processing filter
cascade (highpass + SuperSmoother) appears to produce an oscillator whose
zero-line/threshold crossings are too noisy or too rare for a simple
"buy the dip below 0.2" countertrend rule to hold up out of a narrow
low-vol tercile at daily-bar resolution on these two equity ETFs -- worth
noting for any future Ehlers-family indicator (roofing filter, adaptive
cycle) tests that this filter cascade alone did not transfer well to a
simple threshold-cross entry/exit.

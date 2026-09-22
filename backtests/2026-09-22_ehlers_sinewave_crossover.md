# Backtest Report: Ehlers Sine Wave Two-Line Crossover (2026-09-22)

**Strategy file:** `strategies/2026-09-22_ehlers_sinewave_crossover.py`
**KB id:** 2026-09-22-080
**Outcome: REJECTED**

## Hypothesis
John Ehlers' Sine Wave indicator uses a Hilbert-Transform-derived phase
estimate to plot a Sine line and a LeadSine line (sine of phase + 45°).
Per NinjaTrader Ecosystem ("Buy when the blue line crosses over the red
line") and Stonehill Forex's Sine-Wave-Stochastic confirmation writeup
("Green crosses above Gold = LONG confirmation"), a Sine-crosses-above-
LeadSine event signals entry into a cyclical up-swing; the reverse
crossover signals exit.

This implementation approximates the Hilbert quadrature component with a
fixed-period quarter-cycle lag (rather than the full adaptive MESA
dominant-cycle estimator), parameterized by `cycle_period`. An optional
`SMA(trend_window)` uptrend gate was also tested.

## Grid test summary
- Grid: `cycle_period` in {15, 20, 30} x `trend_window` in {0, 60} x
  symbols {QQQ, SPY} x 3 vol-regime terciles = 36 cells.
- **pass_fraction: 0.361** (13/36 cells clear Sharpe >= 1.0)
- By vol regime: low 11/12 pass, mid 1/12 pass, high 1/12 pass —
  performance concentrated almost entirely in the low-volatility tercile.
- Best single cell: cycle_period=20/trend_window=60, QQQ, low-vol, Sharpe 1.66.

## Full-sample Sharpe (2019-01-01 to 2026-09-01)
| Symbol | cp=15,tw=0 | cp=15,tw=60 | cp=20,tw=0 | cp=20,tw=60 | cp=30,tw=0 | cp=30,tw=60 |
|--------|-----------|-------------|-----------|-------------|-----------|-------------|
| QQQ    | 0.822     | 0.773       | 0.452     | 0.604       | 0.506     | 0.564       |
| SPY    | 0.511     | 0.291       | 0.600     | 0.388       | 0.307     | 0.045       |

Best full-sample config (QQQ, cycle_period=15, trend_window=0) reaches
Sharpe 0.822 — still below the 1.0 threshold. No config clears the bar on
either symbol full-sample.

## Decision
**Reject.** No config passes the full-sample Sharpe >= 1.0 threshold on
either QQQ or SPY; the grid's apparent 36% pass fraction is a low-vol-
regime artifact (11/12 in that tercile alone vs 1/12 in mid and high vol),
not a broadly robust edge. Full validator suite (walk-forward, TC-survival,
parameter sensitivity) was skipped since Sharpe already fails decisively
at every tested grid point (light workload this iteration per gatekeeper
`suggested_workload=light`). Crypto not tested this iteration.

## Sources
- Google SERP: "Ehlers Sine Wave indicator trading strategy specific
  numeric rule lead sine" — ninjatraderecosystem.com/the-sine-wave-indicator/
  link itself 404'd when fetched directly; rule captured from the SERP
  snippet only.
- https://stonehillforex.com/2026/08/ehlers-sine-wave-stochastic-as-a-confirmation-indicator/
  (read via browser_exec fallback — web_search DDGS backend TLS-errored on
  2 consecutive queries this iteration).

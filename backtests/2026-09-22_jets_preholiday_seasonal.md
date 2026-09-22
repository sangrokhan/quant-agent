# Backtest Report: JETS Pre-Holiday Seasonal Hold (D-4 to D-1)

**Strategy file:** `strategies/2026-09-22_jets_preholiday_seasonal.py`
**Date:** 2026-09-22
**Outcome:** REJECTED (near-miss on Sharpe)

## Hypothesis

Per Quantpedia's "Do Airline Stocks Take Off Around U.S. Holidays?"
(https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/,
18 Sep 2026, read via browser_exec this iteration), airline-sector stocks
(proxied by the JETS ETF) exhibit a seasonal return pattern around the 9
major U.S. market holidays, attributed to holiday-travel-driven demand
expectations. Source's disclosed rule for the strongest standalone
window: buy JETS at the close of D-5, hold through D-1, sell at D-1's
close. Source's own reported backtest (2015-2026): CAGR 7.14%,
annualized vol 9.40%, MDD -14.61%, Sharpe 0.76.

First JETS/airline-specific strategy in this repo (0 prior matches
combining "JETS" with a single-asset mechanical rule).

## Step 6 — Grid test summary

Grid: `lookback_days` ∈ {4,5}, `hold_days` ∈ {3,4} × symbols {JETS, SPY}
(equity only, source is equity-specific by nature -- crypto has no
discrete holiday-calendar gap) × 3 vol-regime terciles = 24 cells,
2015-05-01 to 2026-09-01 (JETS ETF inception-constrained start date).

```
pass_fraction: 0.5417 (13/24)
by_vol_regime: low 5/8, mid 4/8, high 4/8
best_cell: lookback_days=5, hold_days=4, SPY, low-vol regime, Sharpe=2.42
worst_cell: lookback_days=5, hold_days=3, JETS, mid-vol regime, Sharpe=0.057
```

## Step 7 — Full-sample validators (source's actual config and asset:
JETS, lookback_days=5, hold_days=4, full sample 2015-05 to 2026-09)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.961 | >= 1.0 | FAIL (near-miss) |
| Max drawdown | 14.8% | <= 25% | PASS |
| Transaction cost survival (10 bps/trade, 84 trades) | 0.838 net Sharpe | >= 0.5 | PASS |
| Walk-forward (manual 4-split) | 4/4 splits positive (1.0) | >= 0.75 | PASS |
| Parameter sensitivity (4-point grid, relative std) | 0.086 | <= 0.5 | PASS |

Our own re-implementation's full-sample Sharpe (0.961) is directionally
consistent with the source's own more conservative reported Sharpe (0.76)
-- both sit close to, but below, this repo's 1.0 minimum-Sharpe bar. The
strategy is otherwise clean: low drawdown, cost-robust, stable across
walk-forward splits and small parameter perturbations.

## Step 8 — Decision: REJECTED (near-miss)

Only the Sharpe threshold fails, by a narrow margin (0.961 vs. 1.0
required), and the source's own reported Sharpe (0.76) is even lower --
this looks like a genuine, modest, real seasonal effect rather than
noise, but it doesn't clear this repo's bar as configured. A future
iteration could revisit this as a direct fix attempt (e.g. combining
JETS D-4..D-1 with the JETS-USO spread leg the source also discloses, or
gating entries to years/holidays with the strongest historical effect) --
flagging this explicitly as a near-miss worth a follow-up rather than a
dead end.

## Source

https://quantpedia.com/do-airline-stocks-take-off-around-u-s-holidays/

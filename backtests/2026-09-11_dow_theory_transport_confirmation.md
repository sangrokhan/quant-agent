# Backtest Report: Dow Theory Industrials/Transports New-High Confirmation

**Strategy file:** `strategies/2026-09-11_dow_theory_transport_confirmation.py`
**Date:** 2026-09-11
**Source:** https://chartschool.stockcharts.com/table-of-contents/market-analysis/dow-theory

## Hypothesis

Per Dow Theory (Charles Dow / William Hamilton / Robert Rhea, codified on
StockCharts ChartSchool), a primary bull-trend signal is only valid when
both the Dow Jones Industrial Average and the Dow Jones Transportation
Average confirm each other by making new highs close together; a
non-confirmation is a warning sign of trend change. This strategy adapts
that rule to single tickers: go/stay long when the traded asset (QQQ/SPY,
"Industrials" role) makes a fresh N-day high AND the confirming asset (IYT,
"Transports" role) also makes a fresh N-day high within a short lag window;
symmetric joint new-low confirmation flips flat. Crypto (BTC vs ETH as
confirm leg) tested as a falsification check since no industrial/transport
sector split exists there.

## Grid test summary (Step 6)

Grid: `lookback_window` in {30,50,75} x `confirm_lag_days` in {3,5,10},
`vol_regime_splits=3`, symbols equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}.

- **Equity:** 21/54 cells passed (pass_fraction 0.389). By vol regime:
  low 18/18 (100%), mid 3/18 (17%), high 0/18 (0%) — the edge lives
  entirely in low-volatility regimes.
  Best cell: lookback_window=50, confirm_lag_days=3, SPY, low-vol, Sharpe 2.76.
  Worst cell: same params, QQQ, high-vol, Sharpe -0.82.
- **Crypto:** 0/54 cells passed (pass_fraction 0.0) across all vol regimes.
  Best cell Sharpe only 0.40 (ETH/USDT, mid-vol). Confirms falsification
  expectation — no genuine sector-confirmation mechanism in crypto.

## Single-config validation (Step 7): lookback_window=50, confirm_lag_days=3

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 0.524 ❌ | 0.572 ❌ | ≥ 1.0 |
| Max drawdown | 0.464 ❌ | 0.336 ❌ | ≤ 0.25 |
| Transaction-cost survival (10bps/trade) | 0.502 ✅ | 0.539 ✅ | ≥ 0.5 |
| Walk-forward (manual 4-split; vbt.utils.splitting broken in this install) | 1.00 (4/4) ✅ | 1.00 (4/4) ✅ | ≥ 0.75 |
| Parameter sensitivity (relative std) | 0.252 ✅ | 0.103 ✅ | ≤ 0.5 |

Full-sample Sharpe and max-drawdown both fail decisively for both symbols,
despite the grid showing a strong signal in low-vol regimes specifically
(100% pass rate there). This is consistent with the grid's own
high-vol-regime results (0% pass, negative Sharpe) — the strategy performs
well in calm markets but suffers large drawdowns and negative risk-adjusted
returns during volatility spikes (e.g. 2020, 2022), dragging the full-sample
Sharpe/MDD below acceptance thresholds even though walk-forward and
parameter-sensitivity are clean.

## Decision: REJECTED

Fails Sharpe and MDD on full sample for both QQQ and SPY. Not a near-miss
(Sharpe ~0.52-0.57 vs 1.0 threshold, MDD ~0.34-0.46 vs 0.25 threshold) —
a decisive full-sample failure despite a promising low-vol-only signal. A
future iteration could revisit this with an explicit high-vol regime gate
(consistent with this repo's repeated finding that trend/breakout signals
need a vol-regime filter to survive full-sample validation) as a direct fix
attempt.

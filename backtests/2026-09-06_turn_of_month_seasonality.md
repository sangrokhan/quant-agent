# Turn-of-the-Month (ToM) Calendar Seasonality — Backtest Report

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_turn_of_month_seasonality.py`
**Outcome:** REJECTED (near-miss on full sample; promising only in isolated mid-vol equity cells)

## Hypothesis

Lakonishok & Smidt (1988): virtually all of the long-run positive excess
return of broad equity indexes accrues during a narrow window straddling
the calendar month boundary (last trading day of month through 3rd trading
day of new month), driven by institutional payroll/pension flow cycles, not
risk. Per Quantpedia's summary: buy 1 day before month end, sell 3rd trading
day of new month.

Sources:
- `google_search:"turn of the month" effect stock market trading strategy rules days` (AI overview + snippets)
- https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes/

## Single-config validator results (best grid config: entry_days_before_month_end=0, exit_days_into_month=5)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel std) |
|---|---|---|---|---|
| QQQ | 0.649 (FAIL, thr 1.0) | 0.214 (PASS, thr 0.25) | 0.329 (FAIL, thr 0.5) | 0.160 (PASS, thr 0.5) |
| SPY | 0.796 (FAIL, thr 1.0) | 0.179 (PASS, thr 0.25) | 0.365 (FAIL, thr 0.5) | 0.178 (PASS, thr 0.5) |

Walk-forward: skipped (repo-wide pre-existing tooling bug — `vectorbt.utils` has no
attribute `splitting` in the installed vectorbt 1.1.0; affects every strategy
tested in this repo, not specific to this one).

## Step 6 grid summary

- Grid: `param_grid={entry_days_before_month_end:[0,1,2], exit_days_into_month:[2,3,5]}`,
  `symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
  period 2015-01-01 to 2026-09-01. 108 total cells.
- `pass_fraction`: 0.185 (20/108)
- `by_asset_class`: equity 20/54 (37%), crypto 0/54 (0% — categorically unsuitable,
  calendar-driven institutional-flow rationale does not apply to a 24/7 crypto market)
- `by_vol_regime`: low 8/36 (22%), mid 11/36 (31%), high 1/36 (3%) — degrades
  sharply in high-vol regimes
- `best_cell`: entry_days_before_month_end=0, exit_days_into_month=5, QQQ,
  mid-vol regime, Sharpe 1.846
- `worst_cell`: entry_days_before_month_end=2, exit_days_into_month=2,
  BTC/USDT, mid-vol, Sharpe -0.170

## Decision

**Rejected.** The full-sample Sharpe at the grid's own best-performing
config fails the 1.0 threshold on both QQQ (0.649) and SPY (0.796), and
transaction-cost-adjusted Sharpe fails decisively on both (0.33/0.36 <
0.5 threshold at 10bps/trade and 279 trades over ~11.7 years — the
strategy trades every month, so transaction costs compound meaningfully
even though each individual holding period is short). Max drawdown and
parameter sensitivity both pass comfortably. The grid's headline best cell
(Sharpe 1.85, mid-vol QQQ) does not generalize to the full sample or to
low/high-vol regimes, indicating the historically-famous ToM anomaly has
likely been arbitraged away or diluted in the modern (2015-2026) sample
relative to the 1897-1986/pre-1988 period the original Lakonishok & Smidt
paper studied — consistent with well-known literature on anomaly decay
post-publication. Crypto is categorically unsuitable (0/54 cells) since
there's no institutional month-end settlement cycle rationale in a 24/7
market.

Worth a future revisit only with a fundamentally different angle (e.g.
combining the calendar window with a trend/vol filter, or testing on a
pre-2010 sample to see if the effect decayed specifically post-2010 as
some literature suggests) rather than the plain calendar-only rule as
tested here.

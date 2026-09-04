# Backtest Report: Payday Anomaly / Mid-Month (16th) Calendar Effect

**Strategy file:** `strategies/2026-09-05_payday_anomaly_midmonth.py`
**Hypothesis id:** 2026-09-05-022
**Source:** https://quantpedia.com/strategies/payday-anomaly/ (Quantpedia summary of the academic "Payday Anomaly" paper)

## Hypothesis

Many US firms pay semi-monthly paychecks on the 15th, with the 401k/retirement-contribution
portion reaching the market on the following trading day (the 16th). Quantpedia reports the
16th calendar day is historically the 3rd-best day of the month for S&P 500 returns. Tested
here as a long-only calendar window strategy: hold during `[signal_day, signal_day+window_days-1]`
calendar days each month, flat otherwise. Tested on equity (QQQ, SPY) and crypto (BTC/USDT,
ETH/USDT, as a falsification check -- no payroll cycle should drive crypto demand).

## Grid test summary (validation/grid_test.py::run_strategy_grid)

- Grid: `signal_day` in {14, 16, 18} x `window_days` in {1, 2, 3} x symbols {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles (low/mid/high), 2019-01-01 to 2026-09-01.
- 108 total cells, **7 passed (pass_fraction = 6.5%)**.
- By asset class: equity 7/54 passed, **crypto 0/54 passed** (as expected -- falsification check confirms no crypto edge).
- By vol regime: low 2/36, mid 1/36, high 4/36 (no regime shows a robust edge either).
- Best cell: `signal_day=14, window_days=1`, SPY, high-vol regime, Sharpe 1.58 (narrow-slice artifact).
- Worst cell: `signal_day=16, window_days=1`, SPY, low-vol regime, Sharpe -1.84.

## Single-config validation (best full-sample config, signal_day=14, window_days=1)

| Symbol | Sharpe | MDD | Net Sharpe after 10bps costs (150/130 trades) |
|---|---|---|---|
| QQQ | 0.95 (fail, thr 1.0) | 3.7% (pass, thr 25%) | 0.29 (fail, thr 0.5) |
| SPY | 0.81 (fail, thr 1.0) | 4.2% (pass, thr 25%) | 0.08 (fail, thr 0.5) |

The literal "16th of month, 2-day window" config (the anomaly as originally described)
performs worse: QQQ Sharpe -0.51, SPY Sharpe -0.83, both fail decisively, MDD also fails
(27-30% > 25% threshold), and net-of-cost Sharpe is deeply negative.

## Verdict: REJECTED

Sharpe fails on both symbols at the best full-sample config found across a 9-value grid
(0.95, 0.81, both < 1.0 threshold); transaction-cost survival also fails (net Sharpe 0.29,
0.08, both < 0.5). The exact literal "16th day" config from the source performs even worse
than the best grid cell. Grid pass_fraction of 6.5% overall, 0% on crypto (falsification
check succeeded -- no crypto edge, consistent with the payroll-driven mechanism), confirms
this doesn't hold up broadly. The historical "16th of month" edge reported by Quantpedia may
be real over a much longer sample (paper's dataset likely spans decades) but is not
detectable/tradable in this repo's ~7.7yr 2019-2026 window, similar to prior thin-sample
calendar-anomaly rejections (Santa Claus Rally 2026-09-05-008, pre-holiday effect
2026-09-03-020).

# Shinohara Intensity Ratio (SIR, Corrected Formula) — Backtest Report

**Hypothesis:** Per ChartIQ's Studies Reference Guide, the true Shinohara
Intensity Ratio is a RATIO OF ROLLING SUMS: StrongRatio = sum(High -
prior Close, floor 0) / sum(prior Close - Low, floor eps); WeakRatio =
sum(High - Close, floor 0) / sum(Close - Low, floor eps). This repo's
prior Shinohara attempt (2026-09-08-051, rejected decisively) used an
incorrect intrabar-close-position formula (SMA of (Close-Low)/(High-Low)
style ratios, resembling %K/Williams %R) rather than this true
prior-close-vs-current-close directional-sum construction. Long entry on
StrongRatio crossing above WeakRatio; exit on reverse cross or
max_hold_days time-stop.

**Source:** Google SERP snippets from ChartIQ SDK documentation
(https://documentation.chartiq.com/) and its Scribd-hosted user guide PDF
mirror -- exact formula text: "The Strong Ratio is a moving sum of a
bar's High less the prior bar's Close divided by the prior Close less
the Low"; "The Weak Ratio is a moving sum of the High-Close divided by
Close-Low."

**Strategy file:** `strategies/2026-09-17_shinohara_intensity_ratio_correct.py`

## Step 6 — Grid test summary (param_grid: sir_window in [14,26,40] x
max_hold_days in [15,30]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 72, passed_cells: 28, **pass_fraction: 0.389**
- by_asset_class: equity 15/36 (42%), crypto 13/36 (36%) -- unlike most
  strategies in this repo, crypto transfers reasonably well here.
- by_vol_regime: low 18/24, mid 6/24, high 4/24.
- best_cell: sir_window=14, max_hold_days=30, QQQ, low-vol regime,
  Sharpe=3.31.

## Step 7 — Single-config validators (full sample, best per-symbol config)

| Validator | QQQ (sir_window=14, hold=30) | SPY (sir_window=14, hold=30) | BTC/USDT (sir_window=40, hold=15) | ETH/USDT (sir_window=40, hold=30) |
|---|---|---|---|---|
| Sharpe (>= 1.0) | PASS 1.085 | PASS 1.110 | FAIL 0.939 | PASS 1.222 |
| Max Drawdown (<= 0.25) | PASS 0.247 | PASS 0.151 | FAIL 0.284 | FAIL 0.429 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.765 (194 trades) | PASS 0.707 (188 trades) | PASS 0.815 (160 trades) | PASS 1.152 (158 trades) |
| Parameter sensitivity (relative_std <= 0.5, 24-cell sir_window x max_hold_days sweep) | **FAIL** 0.620 | PASS 0.449 | PASS 0.168 | PASS 0.180 |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError
bug in this repo's installed vectorbt version, same documented gap as
other entries).

## Outcome: **ACCEPTED (SPY only)**; QQQ near-miss (parameter sensitivity
fail); crypto (BTC/USDT, ETH/USDT) rejected (MDD fail on both, Sharpe
fail additionally on BTC/USDT)

SPY passes all 4 validators cleanly at sir_window=14/max_hold_days=30.
QQQ's headline Sharpe (1.085) and MDD (0.247) both pass at the same
config, but the parameter sweep shows performance is heavily
concentrated at short sir_window values (14) and degrades sharply for
sir_window >= 20 (Sharpe drops to 0.2-0.7 range), giving a relative_std
of 0.62 > the 0.5 threshold -- a real near-miss worth revisiting with a
narrower sir_window search grid or a continuous-sizing-dial transform
(this repo's standard fix for "discrete-signal Sharpe-only near-miss"
patterns, per e.g. 2026-09-15-024's ASI-diff resolution). Crypto fails on
drawdown for both symbols despite reasonable Sharpe on ETH/USDT,
consistent with the correct SIR formula being calibrated toward
lower-volatility trending regimes; not attempting a leverage-cap crypto
rescue this iteration given the scope is already covered by an accepted
equity result.

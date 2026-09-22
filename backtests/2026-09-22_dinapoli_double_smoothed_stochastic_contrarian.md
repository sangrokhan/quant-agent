# Backtest Report: DiNapoli Double-Smoothed Stochastic Contrarian Crossover

**Strategy file:** `strategies/2026-09-22_dinapoli_double_smoothed_stochastic_contrarian.py`
**Date:** 2026-09-22
**Outcome:** REJECTED

## Hypothesis

Per the Backtrader Strategy Compendium's "Mean Reversion" digest
(https://backtrader.readthedocs.io/en/latest/strategies-series/en/02-mean-reversion.html,
Deep Dive 2 "KDJ and DiNapoli — Taming a Twitchy Oscillator", read via
`browser_exec` this iteration), Joe DiNapoli's stochastic recipe uses an
8-period raw %K passed through TWO recursive (Wilder-style) exponential
smoothings (slow_k=3, slow_d=3). The disclosed contrarian rule: the main
smoothed line crossing BELOW the signal line is the BUY signal (opposite of
a standard "golden cross" stochastic trend rule) — betting that the
oscillator's first downward step off a local high anticipates a bounce.
Source ran this on a 6-hour XAUUSD frame: 24 trades / 3 months, 58.3% win
rate, low-frequency/holdable. We added a `max_hold_days` time-stop backstop
(source's own signal is already low-frequency, but no disclosed stop
existed).

No prior DiNapoli-stochastic entries existed in `strategies_index.jsonl`
(0 matches for `DiNapoli.*[Ss]toch`); 3 prior double-smoothed-stochastic
entries (Schaff Trend Cycle, DSS Bressert, Premier Stochastic Oscillator)
use different smoothing constructions/rules.

## Step 6 — Grid test summary

Grid: `k_period` ∈ {8, 14}, `slow_k`=3, `slow_d`=3, `max_hold_days` ∈ {10, 15}
× symbols {QQQ, SPY} (equity) / {BTC/USDT, ETH/USDT} (crypto) × 3 vol-regime
terciles (low/mid/high) = 48 cells, 2019-01-01 to 2026-09-01.

```
pass_fraction: 0.1875 (9/48)
by_asset_class: equity 9/24 passed, crypto 0/24 passed
by_vol_regime:  low 8/16, mid 1/16, high 0/16
best_cell: k_period=14, max_hold_days=10, SPY, low-vol regime, Sharpe=2.37
worst_cell: k_period=14, max_hold_days=10, BTC/USDT, mid-vol regime, Sharpe=-0.86
```

The strategy only shows an edge in equity + low-volatility-regime slices;
it decisively fails on crypto across every vol regime and fails on equity
outside the low-vol tercile.

## Step 7 — Full-sample validators (best config: SPY, k_period=14, slow_k=3,
slow_d=3, max_hold_days=10, full sample 2019-2026, not just the low-vol
slice)

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 0.518 | >= 1.0 | FAIL |
| Max drawdown | 34.1% | <= 25% | FAIL |
| Transaction cost survival (10 bps/trade, 170 trades) | 0.307 net Sharpe | >= 0.5 | FAIL |
| Walk-forward (manual 4-split; `vbt.utils.splitting.RangeSplitter` AttributeError, known repo-wide gap) | 2/4 splits positive (0.50) | >= 0.75 | FAIL |
| Parameter sensitivity (4-point grid, relative std) | 0.101 | <= 0.5 | PASS |

## Step 8 — Decision: REJECTED

The grid's best cell (SPY, low-vol regime only) looked promising
(Sharpe 2.37), but that result does not generalize: full-sample Sharpe on
the same symbol/params is only 0.52, drawdown breaches the 25% cap at
34.1%, and the strategy fails cost-survival and walk-forward robustness.
The edge is narrowly confined to low-volatility equity regimes and does not
survive out of that slice or after realistic transaction costs. Crypto
fails outright across all regimes. The one strength (parameter
insensitivity across the small k_period/max_hold_days grid) does not
offset the full-sample robustness failures.

## Source

https://backtrader.readthedocs.io/en/latest/strategies-series/en/02-mean-reversion.html

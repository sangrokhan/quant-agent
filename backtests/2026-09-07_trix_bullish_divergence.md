# TRIX Bullish Divergence

**Hypothesis:** Per https://theindicatorlab.com/reviews/trix-triple-exponential-average/,
source's own disclosed divergence-trading rule: price making a lower low
while TRIX makes a higher low is a reliable long-entry setup ("the triple
smoothing makes divergence signals more reliable than with MACD"). Entry
gated on TRIX subsequently crossing above zero while the divergence flag is
active; exit on TRIX crossing back below zero or a max_hold_days time-stop.

Source: https://theindicatorlab.com/reviews/trix-triple-exponential-average/.
Distinct from this repo's existing TRIX strategy
(2026-09-04_trix_signalline_crossover.py, signal-line cross while TRIX>0,
no divergence) -- this trades the divergence pattern itself.

## Step 6 — Grid test (length in {10,14,18}, divergence_lookback in
{15,20,30}, equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT} daily bars,
vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 108, passed: 8, **pass_fraction = 0.074** (weakest of the 4
  strategies tested this cron trigger)
- By asset class: equity 5/54, crypto 3/54 -- both weak
- By vol regime: low 5/36, mid 3/36, high 0/36
- Best cell: ETH/USDT, length=10, divergence_lookback=30, mid-vol regime,
  Sharpe 1.143
- Worst cell: ETH/USDT, length=14, divergence_lookback=30, low-vol regime,
  Sharpe -1.198 (same symbol/lookback, opposite vol regime — highly unstable)

## Step 7 — Single-config validators (length=10, divergence_lookback=30,
full unconditional 2019-2026 sample)

| Validator | QQQ | SPY | BTC/USDT | ETH/USDT |
|---|---|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.001 | PASS (degenerate, 0 trades, Sharpe=inf) | FAIL 0.517 | FAIL 0.421 |
| Max Drawdown (<= 0.25) | PASS 0.145 | PASS 0.000 | PASS 0.126 | PASS 0.093 |
| Transaction cost survival | FAIL -0.022 (6 trades) | PASS (degenerate) | PASS 0.505 (8 trades) | FAIL 0.414 (4 trades) |
| Parameter sensitivity (length {10,14,18} sweep, ETH/USDT) | **FAIL NaN/inf** (SPY-style degenerate cell polluted the mean) | | | |

Walk-forward not run: pre-existing `vbt.utils.splitting` AttributeError bug.

## Outcome: **REJECTED**

SPY produced ZERO trades over the full sample at this config (the
divergence+zero-cross compound gate never fired) — a degenerate result, not
a genuine pass, despite the raw Sharpe metric showing infinity. QQQ Sharpe
is essentially zero (0.001) and fails transaction-cost survival outright.
BTC/USDT and ETH/USDT both miss the Sharpe bar. The lowest grid
pass_fraction of any strategy tested this cron trigger (0.074), with wild
Sharpe swings between adjacent vol regimes for the same symbol/config
(ETH/USDT +1.14 mid-vol vs -1.20 low-vol at length=14) indicating an
unstable, non-robust signal. The divergence-detection logic (shared
construction with the KST divergence strategy tested earlier this run,
2026-09-07-017, also rejected) again produces too few, too unreliable
trades to clear the bar.

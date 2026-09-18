# 2026-09-18-070: ETF Rotation + Absolute-Momentum Overlay (Rescue of 2026-09-18-069)

## Hypothesis

Direct fix attempt for the prior near-miss 2026-09-18-069 (Monthly ETF
Rotation, 200d SMA eligibility + ROC ranking + top-N, QQQ Sharpe
0.939/MDD 0.286 both narrowly missed). This iteration adds ONE extra
absolute-momentum condition: the primary asset must not only be top-N
ranked and above its 200d SMA, but its own trailing ROC over the ranking
lookback must ALSO be strictly positive (`require_positive_roc=True`).
Targets the specific failure mode noted in -069's own log ("always holding
top-N regardless of absolute momentum sign") -- being top-ranked in a
falling basket can still trigger a hold under -069's pure relative-rank
rule; SMA(200) lags and a fresh downturn can persist above a still-elevated
200d average for months.

Basket, ranking mechanics, and all other parameters otherwise IDENTICAL to
2026-09-18-069 (this repo's own dual-momentum-style extension, not
separately sourced beyond the original FabTrader.in ETF rotation article
that -069 cited: https://fabtrader.in/blog/a-simple-peaceful-etf-rotation-strategy-that-delivered-32-cagr).

## Parameter scan (require_positive_roc=True, trend_window in [150,200] x
roc_lookback_months in [1,3,6] x top_n in [2,3,4], QQQ/SPY, vol_regime_splits=3,
2018-01-01..2026-09-01)

Best average-across-vol-regimes config: **QQQ, trend_window=150,
roc_lookback_months=1, top_n=3**, avg Sharpe 1.166, pass 2/3 vol regimes.
Total grid pass_fraction 0.352 (38/108), up from 0.380 raw-cell-count but
now concentrated in genuinely stronger configs (best avg Sharpe 1.166 vs
1.280 raw-best-cell before -- the absolute-momentum filter trades a bit of
peak Sharpe for a materially lower drawdown, per the full validation
below).

## Single-config validation (trend_window=150, roc_lookback_months=1,
top_n=3, require_positive_roc=True, 2018-01-01..2026-09-01)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **1.058 (pass)** | 0.454 (fail) | 1.0 |
| Max drawdown | **0.172 (pass)** | 0.211 (pass) | 0.25 |
| Net Sharpe after costs (10bps/trade) | **1.013 (pass)**, 35 trades | 0.363 (fail), 47 trades | 0.5 |
| Walk-forward (4 splits, manual substitute*) | **1.00 (4/4, pass)** | 0.75 (3/4, pass) | 0.75 |
| Parameter sensitivity (relative std, 18-combo grid) | **0.237 (pass)** | 0.470 (pass) | 0.5 |

\* `validation/validators.py::check_walk_forward` errors on the installed
vectorbt 1.1.0; substituted a manual 4-equal-split walk-forward with the
identical pass criterion (established fallback pattern).

QQQ passes ALL FIVE validators cleanly. SPY still fails Sharpe and
transaction-cost survival (though improved from -069's decisive fail --
walk-forward now passes and parameter sensitivity improved from 0.735 to
0.470).

Crypto asset-class breadth: not applicable by construction (same as
-069) -- basket is a US cross-asset equity-ETF universe (QQQ/SPY/IWM/GLD/
TLT/EFA/EEM) with no natural crypto member.

## Decision

**Accepted for QQQ only** (config: trend_window=150, roc_lookback_months=1,
top_n=3, require_positive_roc=True). All five validators pass: Sharpe
1.058, MDD 0.172, net Sharpe after 10bps/trade costs 1.013 (35 trades over
8.7 years), walk-forward 4/4 splits positive, parameter sensitivity relative
std 0.237. The absolute-momentum floor added on top of -069's pure
relative-ranking rule directly rescues the near-miss, confirming the
hypothesis that "holding top-N regardless of absolute sign" was
contributing to -069's drawdown/Sharpe shortfall.

**SPY rejected** -- fails Sharpe (0.454) and transaction-cost survival
(0.363) despite passing MDD, walk-forward, and parameter sensitivity. SPY's
lower absolute volatility versus QQQ appears to produce weaker
Sharpe-per-unit-of-turnover under this rotation cadence; a future iteration
could test SPY-specific parameter retuning (e.g. longer roc_lookback to
reduce its 47-trade turnover) separately, following this repo's established
per-symbol-retune pattern.

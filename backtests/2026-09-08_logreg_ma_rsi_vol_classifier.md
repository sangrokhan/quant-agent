# Backtest Report: Logistic Regression MA/RSI/Volume Classifier (2026-09-08)

**Status: REJECTED** — strategy file kept in `strategies/` as a record.

## Hypothesis

Per QuantInsti "Machine Learning Logistic Regression: Python, Trading, and
More" (https://blog.quantinsti.com/machine-learning-logistic-regression-python/),
a worked example builds a binary classifier for next-day up/down direction
using three predictors: MA(50/200) crossover binary, RSI value, and trading
volume, buying when the predicted probability of an up day exceeds a
threshold (source example: p > 0.7).

Implemented as a rolling walk-forward `sklearn.LogisticRegression`, refit
every `refit_every` days on trailing `train_window` days, strictly
no-lookahead.

## Single-config validator results (best grid config: `prob_threshold=0.52`, `refit_every=42`, QQQ)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.989 | ≥ 1.0 | ❌ (narrow miss) |
| Max drawdown | 0.286 | ≤ 0.25 | ❌ |
| Net Sharpe after costs (10bps, 47 trades) | 0.947 | ≥ 0.5 | ✅ |
| Walk-forward pass fraction (4 splits) | 0.5 (2/4 positive) | ≥ 0.75 | ❌ |
| Parameter sensitivity relative std | 0.060 | ≤ 0.5 | ✅ |

## Grid test summary

`param_grid={prob_threshold:[0.52,0.55]}` (refit_every fixed at 42 for
compute-budget reasons — see note below), `symbols={equity:[QQQ,SPY],
crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3` (2019-01-01 to
2026-09-01), 24 total cells.

- Overall pass_fraction: 0.25 (6/24 cells)
- By asset class: equity 6/12 passed, crypto 0/12
- By vol regime: low 4/8, mid 2/8, high 0/8
- Best cell: QQQ, low-vol, `prob_threshold=0.52`, Sharpe 1.992
- Worst cell: SPY, mid-vol, `prob_threshold=0.55`, Sharpe -0.655

## Decision

**Reject.** QQQ's best config fails 3 of 5 validators: Sharpe narrowly below
threshold (0.989), max drawdown above threshold (0.286), and — most
tellingly — walk-forward only 2 of 4 chronological quarters show positive
Sharpe (0.5 pass fraction vs 0.75 required), indicating an unstable
out-of-sample edge despite the model passing the coarse parameter-sensitivity
sweep tested. Crypto rejected decisively (0/12 cells).

**Compute-cost note for future ML-strategy iterations:** rolling
walk-forward refit strategies (this one, and the earlier HMM regime filter
2026-09-08-173) are 10-100x slower per grid cell than rule-based strategies
due to per-cell model fitting — a 24-cell grid at `refit_every=42` took
~10 minutes; `refit_every=21` was prohibitively slow within this iteration's
budget. Only 2 `prob_threshold` values were tested as a result; keep future
ML-strategy grids small and consider caching feature engineering across
param combos if this pattern recurs.

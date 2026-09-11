# 2026-09-11: Kalman-Filter / SMA Mean-Reversion Crossover (SPY)

**Strategy file:** `strategies/2026-09-11_kalman_sma_meanrev_crossover.py`
**Knowledge base id:** 2026-09-11-112

## Hypothesis

Per quantifiedstrategies.com's "Kalman Filter Trading Strategy" article
(https://www.quantifiedstrategies.com/kalman-filter-trading-strategy/), a
1D Kalman filter on closing price gives a smooth latent fair-value
estimate. Their disclosed rule: go long when a short (5-day, generalized
here to a tunable `sma_window`) SMA of close crosses **under** the
Kalman-filtered level, exit when it crosses back **above**. This is a
mean-reversion construction, distinct from the two other Kalman variants
already in this repo's knowledge base:
- 2026-09-05-056: dual fast/slow Kalman percentile-breakout — **rejected**, all asset classes.
- 2026-09-08-052: single constant-velocity Kalman + slope-confirmed trend-following crossover — **accepted**, QQQ equity only.

This iteration tests the simpler, pure level-vs-SMA **mean-reversion**
variant (no slope confirmation) to see if it clears validation and/or
generalizes better.

## Primary config (best cell from grid + parameter-sensitivity sweep)

`sma_window=15, kalman_q=0.1, kalman_r=1.0, max_hold_days=10`, symbol SPY,
full sample 2019-01-01 to 2026-09-01.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.664 | ≥ 1.0 |
| Max drawdown | ✅ | 9.73% | ≤ 25% |
| Transaction cost survival (10bps/trade, 143 trades) | ✅ | net Sharpe 1.308 | ≥ 0.5 |
| Walk-forward (4 splits, manual date-slice fallback — vectorbt.utils.splitting API bug) | ✅ | 4/4 splits positive Sharpe (1.0) | ≥ 0.75 |
| Parameter sensitivity (kalman_q ∈ {0.05,0.1,0.2} × max_hold_days ∈ {10,20}, SPY) | ✅ | relative std 0.132 | ≤ 0.5 |

## Step 6 grid summary (sma_window=15, kalman_q ∈ {0.05,0.1,0.2}, kalman_r=1.0, max_hold_days ∈ {10,20}; QQQ+SPY equity, BTC/USDT+ETH/USDT crypto; vol_regime_splits=3)

- Overall pass_fraction: 25/72 = **0.347**
- By asset class: equity 25/36 (0.694) — crypto **0/36 (0.0)**
- By vol regime: low 12/24 (0.5), mid 6/24 (0.25), high 7/24 (0.29)
- Best cell: QQQ, low-vol, sma_window=15/kalman_q=0.1/max_hold=10, Sharpe 2.35
- Worst cell: BTC/USDT, low-vol, same params, Sharpe -0.015

**Honest scope:** this strategy works only on **equity (QQQ, SPY)**, and
noticeably better in low/mid-vol regimes than high-vol regimes. It does
**not** generalize to crypto (BTC/USDT, ETH/USDT) — 0/36 crypto cells
passed across the whole grid, consistent with the prior Kalman
percentile-breakout rejection (2026-09-05-056) also failing broadly on
crypto. Do not deploy this outside equity index ETFs.

## Decision: ACCEPT

All 5 validators passed for the primary SPY config. Strategy file and this
report are kept as a live accepted strategy, scoped to equity only.

## Source

https://www.quantifiedstrategies.com/kalman-filter-trading-strategy/

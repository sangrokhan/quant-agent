# Bottom-of-the-Range Up-Day IBS Fade (fixed 3-day time-stop) — QQQ Backtest Report

**Date:** 2026-09-21 (cron trigger, iteration 4)
**Strategy file:** `strategies/2026-09-21_bottom_of_range_updayibs_timestop.py`
**Hypothesis source:** https://www.quantifiedstrategies.com/the-bottom-of-the-range-trading-strategy/
(fully free/disclosed, found via web_search which worked normally this
iteration)

## Hypothesis

Per quantifiedstrategies.com's "The Bottom Of The Range Trading Strategy"
article: IBS = (close-low)/(high-low) < 0.1 (today's bar finished very near
its own low despite closing UP on the day) combined with today's close >
yesterday's close signals a long entry at today's close, exited after a
fixed 3-day time-stop. Source's own SPY backtest (2005-present): only 14
trades, 12 winners, avg gain 0.76%, 10.69% cumulative return -- a rare,
low-frequency setup.

## Grid test summary (ibs_threshold x hold_days x symbol x vol-regime)

- Grid: `ibs_threshold` in {0.1, 0.15, 0.2}, `hold_days` in {2, 3, 5};
  symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto); 3 vol-regime terciles.
- **Total cells:** 108, **Passed:** 12, **pass_fraction = 0.111**
- By asset class: equity 12/54; crypto 0/54 (complete failure on crypto).
- By vol regime: low 5/36, mid 5/36, high 2/36 -- spread thinly across all
  three regimes, no clear regime concentration.
- Best average full-sample QQQ cell: (ibs_threshold=0.2, hold_days=3), avg
  Sharpe 0.983 -- already below the 1.0 threshold on average, and this was
  the best of the 9 param combos tested.

## Single-config validation, QQQ, full sample 2016-2026 (ibs_threshold=0.2, hold_days=3)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.961 | 1.0 |
| Max drawdown | ✅ | 0.055 | 0.25 |
| Transaction cost survival (10bps/trade, 38 trades) | ✅ | 0.783 net Sharpe | 0.5 |
| Walk-forward (4 splits) | ✅ (marginal) | 0.75 pass fraction | 0.75 |
| Parameter sensitivity (9-cell QQQ grid) | ❌ | 0.746 relative std | 0.5 |

Two validators failed: Sharpe (0.961, just under the 1.0 threshold) and
parameter sensitivity (0.746 relative std, well above the 0.5 threshold --
the strategy's performance is quite sensitive to the exact
ibs_threshold/hold_days combination chosen, indicating a risk of overfitting
to any single config).

## Decision: REJECT

Even after loosening the source's own IBS threshold from 0.1 to 0.2 (the
grid's best-performing config), the strategy fails both the Sharpe threshold
and — more importantly — parameter sensitivity, meaning the modest edge seen
in some grid cells is not robust across nearby parameter values. Very low
max drawdown and reasonable transaction-cost survival, but not enough to
overcome the primary Sharpe/sensitivity failures. Strategy file and this
report are kept as a record of a rejected attempt.

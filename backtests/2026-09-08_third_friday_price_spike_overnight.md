# Backtest Report: Third-Friday Price Spike Overnight Hold

**Strategy file:** `strategies/2026-09-08_third_friday_price_spike_overnight.py`
**Date:** 2026-09-08
**Status:** REJECTED (decisive)

## Hypothesis

Per Baltussen, Terstegge & Whelan, "The Derivative Payoff Bias"
(summarized at https://www.quantitativo.com/p/the-derivative-payoff-bias):
S&P 500 index options/futures settling via the Special Opening Quotation
(3rd Friday's opening price) experience systematic dealer Charm-hedging
buy pressure overnight into that SOQ window ("Third Friday Price Spike").
Adapted (daily-bar loaders can't express the source's intraday
short-before-noon reversal leg) as a long-only overnight hold entered at
Thursday's close, exited at Friday's open, active ONLY during 3rd-Friday-
of-month weeks.

## Full-sample single-config metrics (week_offset=0)

| Symbol | Sharpe | Max DD | Net Sharpe (5bps/trade) | Walk-forward | Trades |
|---|---|---|---|---|---|
| SPY | -0.437 (fail) | 0.098 (pass) | -0.604 (fail) | 0.25 (fail) | 88 |
| QQQ | 0.459 (fail) | 0.043 (pass) | -0.071 (fail) | 0.50 (fail) | 88 |

## Step 6 grid summary (week_offset ∈ {-1,0,1}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles)

- Total cells: 36, passed (Sharpe≥1.0 & MDD≤0.25): 3 → **pass_fraction 0.083**
- By asset class: equity 3/18; crypto 0/18 (expected -- no options-expiration SOQ mechanism on 24/7 crypto)
- By vol regime: low 2/12, mid 1/12, high 0/12
- Best cell: week_offset=0, QQQ, low-vol regime, Sharpe 1.741 (isolated)
- Worst cell: week_offset=1, SPY, high-vol regime, Sharpe -2.231

The isolated low-vol-regime edge does not survive to the full-sample test:
both SPY and QQQ post negative-to-marginal Sharpe, fail transaction-cost
survival, and fail walk-forward robustness (only 1-2 of 4 chunks positive).
This is consistent with the source's own paper being about INDEX
DERIVATIVES/FUTURES settlement mechanics (SOQ pricing, Charm-hedging by
options market makers) -- a mechanism that doesn't necessarily transmit
cleanly to the underlying cash ETF's own close-to-open return, especially
once the adaptation drops the source's own short-reversal leg (which the
source states is where a meaningful part of the tradeable edge comes from,
since the pattern is "tent-shaped": up overnight, DOWN intraday). This
repo's daily-bar loaders cannot express that second leg.

## Verdict

REJECTED (decisive) — full-sample Sharpe, transaction-cost survival, and
walk-forward all fail for both SPY and QQQ; the grid's isolated low-vol
near-miss does not generalize. Crypto rejected decisively (0/18, expected
-- no options-expiration mechanism). The underlying paper's actual edge
likely requires the intraday short-reversal leg this repo's daily-bar
loaders cannot express, not just the overnight long leg tested here.

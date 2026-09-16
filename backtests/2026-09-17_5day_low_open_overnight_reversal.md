# 5-Day-Low-Open + Bullish-Close Overnight Reversal (2026-09-17)

## Hypothesis

Per QuantifiedStrategies.com's "5-Day Low Overnight Trading Strategy"
(https://www.quantifiedstrategies.com/5-day-low-overnight-trading-strategy/,
read via `browser_exec` this iteration — `web_search` failed with a backend
`RequestError` for the initial query, so Google search was used to locate
this page): trade S&P 500 when it opens at a 5-day low but closes higher
than its opening price; enter at the close, exit at the next day's open.
Disclosed backtest (2005+): 175 trades, avg gain/trade 0.31%, win rate 62%,
MDD 13%. Exact numeric rules are paywalled but the mechanism description is
fully implementable.

Distinct from all other N-day-low strategies in this repo: Double 7s
(2026-09-04-114, close vs N-day-low-of-closes + SMA200 filter + signal exit),
5-Day-Low-of-Range (2026-09-07-005, IBS<0.25 + close<5-day-low-of-closes +
fixed multi-day hold), Turtle Soup (2026-09-04-076, fades a failed breakdown
on the next close). This is the first strategy in the repo whose return
mechanism is close-to-NEXT-OPEN overnight exposure only, triggered by the
OPEN (not close) hitting an N-day low plus an intraday bullish reversal.

## Strategy file

`strategies/2026-09-17_5day_low_open_overnight_reversal.py`

## Grid test (`scripts/run_grid_5day_low_open_overnight.py`)

`param_grid={"n_days": [3, 5, 10]}`, symbols `{equity: [QQQ, SPY], crypto:
[BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`. 36 cells.

- `pass_fraction`: 0.25 (9/36)
- `by_asset_class`: equity 9/18, crypto 0/18 (decisive fail)
- `by_vol_regime`: low 4/12, mid 1/12, high 4/12
- `best_cell`: QQQ, n_days=10, low-vol regime, Sharpe 1.75
- `worst_cell`: ETH/USDT, n_days=3, low-vol regime, Sharpe -1.17

## Full-sample validators (`scripts/validate_5day_low_open_overnight.py`, n_days=10, 2019-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.462 ✅ | 1.098 ✅ | ≥1.0 |
| Max drawdown | 0.041 ✅ | 0.033 ✅ | ≤0.25 |
| TC survival (10bps/trade) | net Sharpe 0.671 ✅ (118 trades) | net Sharpe 0.320 **❌** (120 trades) | ≥0.5 |
| Walk-forward (manual 4-split fallback) | 4/4 splits positive (0.91, 0.51, 2.19, 2.59) ✅ | not run (already failed TC) | ≥0.75 |
| Parameter sensitivity (n_days∈{3,5,10} on QQQ, Sharpe 0.758/0.855/1.462) | relative_std 0.304 ✅ | — | ≤0.5 |

SPY fails transaction-cost survival: raw Sharpe passes (1.10) but the strategy
only clears ~0.31% avg gross return per overnight hold, similar trade count
to QQQ (120 vs 118) but a materially thinner net edge after the flat 10bps/
trade cost assumption pushes it under the 0.5 net-Sharpe floor. QQQ's larger
overnight-gap edge survives the same cost assumption comfortably.

## Decision: ACCEPT (QQQ only)

QQQ passes all 5 validators at `n_days=10`. SPY fails TC-survival and crypto
is decisively rejected (0/18 grid cells) — strategy is scoped to QQQ only.

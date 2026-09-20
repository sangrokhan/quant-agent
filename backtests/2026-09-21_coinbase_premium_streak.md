# Coinbase Premium Index Streak-Based BTC/ETH Long — Backtest Report (2026-09-21)

## Hypothesis

Per crypto.news's "What is the Coinbase Premium Index?" guide
(https://crypto.news/what-is-the-coinbase-premium-index/, read via
browser_exec fallback this iteration — web_search backend intermittently
TLS-erroring): the Coinbase Premium Index measures the % gap between BTC
quoted in USD on Coinbase (the dominant US-regulated venue, hard-wired to
the spot-BTC-ETF creation/redemption plumbing) and BTC quoted in USDT on a
global reference venue (Binance). The source's own explicit reading
framework: "Read streaks, not prints... The informative patterns are runs:
five, ten, fourteen consecutive days on one side of zero." Tested here: go
long BTC/ETH when the premium has held positive for at least `streak_days`
consecutive days (persistent US-institutional demand signal); exit when the
premium flips negative or a time-stop is hit.

Source URL: https://crypto.news/what-is-the-coinbase-premium-index/

This is a genuinely novel angle for this repo — no prior cross-exchange
premium strategy exists — and was confirmed feasible: `ccxt`'s `coinbase`
exchange is available via `data/loaders.py::load_crypto(..., exchange=
"coinbase")` for both BTC/USD and ETH/USD.

## Strategy file

`strategies/2026-09-21_coinbase_premium_streak.py`

## Grid test summary (Step 6, crypto-only — mechanism is inherently
crypto-specific, no equity analog exists)

- Grid: `streak_days` ∈ {3, 5, 8}, `max_hold_days` ∈ {10, 20}
- Symbols: BTC/USDT, ETH/USDT (Binance leg; Coinbase leg fetched
  internally per-symbol)
- Vol regime splits: 3
- Total cells: 36, passed: 3, **pass_fraction = 0.083**
- By symbol: BTC/USDT 3/18 passed (avg Sharpe 0.624), ETH/USDT 0/18 passed
  (avg Sharpe 0.723, but the one high-Sharpe cell — streak_days=3,
  max_hold=10, low-vol, Sharpe=1.53 — failed max drawdown at 28.8% > 25%
  threshold)
- By vol regime: low 2/12, mid 1/12, high 0/12
- Best cell: ETH/USDT, streak_days=3, max_hold_days=10, low-vol,
  Sharpe=1.53 (MDD fails)
- Worst cell: ETH/USDT, streak_days=8, max_hold_days=20, mid-vol,
  Sharpe=-0.05

## Decision: REJECTED

Pass fraction of 8.3% and modest average Sharpe (0.6-0.7) on both BTC and
ETH indicate the premium-streak signal, as operationalized here, does not
translate the source's own qualitative reading framework into a robust
mechanical edge over this repo's 2018-2026 crypto sample. The one
attractive cell (ETH, short streak/short hold, low-vol) fails on drawdown
alone, suggesting the position sizing/exit logic (simple long-flat, no
stop-loss beyond the time-stop) is too blunt an instrument for what the
source frames as a nuanced, multi-signal ("read it inside a dashboard,
never alone") read. A future iteration could pair this premium streak with
an explicit stop-loss or combine it with the source's own "direction of
change" (shrinking-negative-streak reversal) signal rather than a bare
sign-streak threshold.

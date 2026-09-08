# Backtest Report: Intramonth Momentum Cycle Window

**Strategy file:** `strategies/2026-09-08_intramonth_momentum_cycle_window.py`
**Date:** 2026-09-08
**Status:** REJECTED

## Hypothesis

Per Nathan, Suominen & Tasa, "The Intramonth Momentum Cycle" (SSRN 2026,
via Google SERP: "U.S. equity momentum returns concentrate in six trading
days each month, ending four trading days before month-end") and its
sector-ETF extension "Sectoral Intramonth Momentum Cycle"
(https://quantpedia.com/sectoral-intramonth-momentum-cycle-exploiting-turn-of-the-month-patterns-in-sector-etf-strategies/):
momentum's edge concentrates in a narrow intramonth window and
decays/reverses approaching month-end (consistent with turn-of-month
rebalancing flows). Implemented at the index-ETF level: hold an absolute
momentum long position (trailing `lookback_months`-month return positive)
ONLY during a `window_days`-day block ending `end_offset` trading days
before month-end, flat all other days.

## Full-sample single-config metrics (lookback_months=12, window_days=6, end_offset=2 — matches the source's own disclosed 6-day/4-day-before-end structure, adjusted end_offset to the grid's best cell)

| Symbol | Sharpe | Max DD | Net Sharpe (5bps/trade) | Walk-forward | Param sensitivity (rel std) | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.314 (fail) | 0.131 (pass) | 0.153 (fail) | 0.50 (fail) | 0.250 (pass) | 66 |
| QQQ | 0.465 (fail) | 0.183 (pass) | 0.342 (fail) | 0.75 (pass) | 0.093 (pass) | 68 |

## Step 6 grid summary (lookback_months ∈ {6,12} × window_days ∈ {4,6,8} × end_offset ∈ {2,4}, equity {QQQ,SPY} + crypto {BTC/USDT,ETH/USDT}, 3 vol-regime terciles)

- Total cells: 144, passed (Sharpe≥1.0 & MDD≤0.25): 23 → **pass_fraction 0.160**
- By asset class: equity 23/72; crypto 0/72 (expected -- the paper's mechanism is anchored to institutional month-end rebalancing flows around a discrete monthly calendar, which don't structurally apply to 24/7 crypto)
- By vol regime: **low 23/48 (100% of all passes)**, mid 0/48, high 0/48 -- edge exists exclusively in the low-vol tercile
- Best cell: lookback_months=12, window_days=6, end_offset=2, SPY, low-vol regime, Sharpe 1.931
- Worst cell: lookback_months=12, window_days=8, end_offset=4, SPY, mid-vol regime, Sharpe -0.926

The grid's low-vol-only edge (isolated to 1/3 of the vol-regime terciles)
does not generalize to the full unconditioned sample: both SPY and QQQ
post Sharpe well below 1.0 (0.31 / 0.46) and fail transaction-cost
survival even at a modest 66-68 round-trip entries over 7.5 years. Walk-
forward and parameter sensitivity pass for QQQ but SPY's walk-forward
fails outright (only 2/4 chunks positive). This index-ETF-level adaptation
of a signal the original paper documents at the individual-stock (and
sector-ETF, in the Quantpedia extension) cross-sectional level likely
loses most of its edge -- a single-ETF absolute-momentum timing signal is
a much weaker proxy than the paper's actual cross-sectional relative
momentum ranking mechanism.

## Verdict

REJECTED — full-sample Sharpe and transaction-cost survival fail
decisively for both SPY and QQQ despite a promising isolated low-vol-
regime grid cell (Sharpe 1.93); the edge is entirely concentrated in one
vol-regime tercile and does not survive to the unconditioned full sample.
Crypto rejected decisively (0/72, expected). A future iteration could
revisit this at the SECTOR-ETF cross-sectional level (the paper's actual
tested structure: rank multiple sector ETFs by momentum and go long/short
the extremes during the intramonth window) rather than a single-ETF
absolute-momentum timing signal, which this repo's current single-symbol
`generate_returns_fn(price_df, **params)` grid-test contract doesn't
directly support without a cross-sectional ranking extension.

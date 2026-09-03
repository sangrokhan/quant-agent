# Backtest Report: Time-Series Short-Term Reversal (Single-Asset)

**Strategy file:** `strategies/2026-09-03_ts_short_term_reversal.py`
**Date:** 2026-09-03
**Hypothesis id:** 2026-09-03-009

## Hypothesis

Source: https://quantpedia.com/strategies/short-term-reversal-in-stocks --
the well-documented cross-sectional short-term reversal anomaly: stocks with
low trailing weekly/monthly returns earn positive abnormal returns the
following period, and vice versa. Attributed to investor overreaction /
correction, and/or compensation for liquidity provision (Nagel,
"Evaporating Liquidity"). The source's own strategy is a cross-sectional
decile-sort across a broad stock universe (buy losers/sell winners,
restricted to large-cap to survive costs) -- not directly implementable with
this repo's single-symbol `data/loaders.py`.

Adapted to a single-asset time-series analog: after a short (`lookback_days`)
period of negative cumulative return, go long for a fixed `hold_days`
holding period, betting on a short-lived bounce; flat otherwise, long-only.

## Step 6 — Grid test summary

Grid: `lookback_days ∈ {3,5,10}` × `entry_threshold ∈ {0.02,0.04}` ×
`hold_days ∈ {3,5}` × symbols `{QQQ,SPY}` (equity), `{BTC/USDT,ETH/USDT}`
(crypto) × 3 vol terciles. 144 cells, 2019-01-01 to 2026-09-01.

| Slice | Passed / Total |
|---|---|
| Overall | 14 / 144 (9.7%) |
| Equity | 14 / 72 (19.4%) |
| Crypto | 0 / 72 (0.0%) |
| Low-vol | 10 / 48 (20.8%) |
| Mid-vol | 0 / 48 (0.0%) |
| High-vol | 4 / 48 (8.3%) |

Best cell: `lookback_days=5, entry_threshold=0.02, hold_days=5`, SPY,
low-vol regime, Sharpe 2.59 -- but this is a narrow, low-vol-only tercile
result. Worst cell: `lookback_days=10, entry_threshold=0.02, hold_days=5`,
QQQ, mid-vol, Sharpe -1.10.

**Overall pass fraction is low (9.7%) and concentrated almost entirely in
low-vol equity slices** -- unlike the accepted Donchian strategy
(2026-09-03-008), this does not even hold up robustly across mid-vol equity
regimes, let alone crypto.

## Step 7 — Single-config validation (best config: SPY, lookback_days=5, entry_threshold=0.02, hold_days=5, full 2019-2026 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.54 | ≥ 1.0 |
| Max drawdown | ✅ | 21.8% | ≤ 25% |
| Transaction cost survival (10bps/trade, 91 trades) | ❌ | net Sharpe 0.42 | ≥ 0.5 |
| Walk-forward (4 contiguous OOS windows, manual fallback -- see notes) | ✅ | 4/4 splits positive Sharpe (100%) | ≥ 75% |
| Parameter sensitivity (12-point grid on SPY) | ✅ | relative std 0.44 | ≤ 0.5 |

Same `check_walk_forward` vectorbt API bug as the prior iteration
(`vectorbt.utils.splitting.RangeSplitter` missing) -- worked around with the
same manual 4-window date-slice fallback.

## Decision: **REJECT**

The full-period Sharpe on the best grid cell's own config (0.54) is far
below the low-vol-tercile-only cell's Sharpe (2.59) that made it "best" in
the grid -- i.e. the edge is real but concentrated almost entirely in calm
markets and mostly evaporates (net of ~91 round-trip entries' worth of
transaction costs) once mid/high-vol periods and the full sample are
included. Both the primary Sharpe gate and the transaction-cost-survival
gate fail. This is consistent with the source article's own caveat that
short-term reversal profits are fragile to transaction costs and turnover --
here even a single-asset, long-only, fixed-hold adaptation with only ~13
trades/year still can't clear the cost-survival bar at the full-sample
level. Strategy file and this report are kept as a record of a rejected
attempt (not live).

# Gann HiLo Activator flip + SMA trend filter — backtest report

**Strategy file:** `strategies/2026-09-04_gann_hilo_activator_trendfilter.py`
**Hypothesis id:** 2026-09-04-128

## Hypothesis

The Gann HiLo Activator (W.D. Gann concept, popularized by Robert Krausz,
*Stocks & Commodities* V16:2) is a stepped trailing support/resistance line:
in an "up" state it plots the SMA of trailing lows (support); in a "down"
state it plots the SMA of trailing highs (resistance). It flips state
whenever price closes through the opposite line. Per
[enlightenedstocktrading.com](https://enlightenedstocktrading.com/gann-hillo-activator/):
"A rules-based strategy using the Gann HiLo Activator might involve buying
when the indicator flips from resistance to support and selling when it
flips back", combined with a longer-term SMA trend filter to reduce
whipsaws in choppy/range-bound markets (the article's own recommended risk
mitigation). Tested here: long entry on flip-to-up AND close above a
100-day SMA; exit on flip-to-down or a 15-day time-stop.

Source: https://enlightenedstocktrading.com/gann-hillo-activator/ (via
browser_exec Google-search fallback after web_search's DDGS/Yahoo backend
returned a connection error for the query).

## Grid summary (Step 6)

`period` in {8,10,14} x `trend_window` in {50,100} x `max_hold_days`
in {10,15}, symbols QQQ/SPY/BTC/USDT/ETH/USDT, vol_regime_splits=3:

- 144 cells total, 34 passed (pass_fraction=0.236)
- by_asset_class: equity 34/72, crypto 0/72
- by_vol_regime: low 20/48, mid 6/48, high 8/48
- best_cell: period=14, trend_window=100, max_hold_days=15, SPY, low-vol, Sharpe=2.97
- worst_cell: period=8, trend_window=50, max_hold_days=15, QQQ, high-vol, Sharpe=-0.69

## Primary config validators (period=14, trend_window=100, max_hold_days=15)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.320 **FAIL** | 1.038 **PASS** |
| Max drawdown (<=0.25) | 0.214 PASS | 0.110 PASS |
| Net Sharpe after costs (>=0.5, 10bps/trade) | 0.216 **FAIL** (58 trades) | 0.877 PASS (51 trades) |
| Walk-forward (4-split, >=0.75 pass_frac) | 0.50 **FAIL** | 0.75 PASS |
| Parameter sensitivity (rel.std<=0.5, period in {8,10,14}) | 0.231 PASS | 0.276 PASS |

## Decision

- **QQQ: reject.** Fails Sharpe, TC-survival, and walk-forward decisively.
- **SPY: accept.** All 5 validators pass at the grid-best config.
- **Crypto: reject.** 0/72 grid cells passed.

Net outcome: accepted for SPY only (period=14, trend_window=100,
max_hold_days=15); rejected for QQQ and crypto. Consistent with the
recurring pattern in this log where SPY's lower realized vol lets
trend-following flip/crossover systems clear the Sharpe/TC bar more often
than QQQ at the same parameters.

# Backtest Report: "Sell in August and Go Away" 10-Month Seasonality

**Strategy file:** `strategies/2026-09-20_sell_in_august_10mo_seasonality.py`
**Date:** 2026-09-20
**Source:** Cesar Alvarez (Alvarez Quant Trading),
https://alvarezquanttrading.com/blog/sell-in-august-and-go-away/ (read via
browser_exec after web_search DDGS/Yahoo backend TLS-errored on every
query this iteration).

## Hypothesis

Re-testing Jay Kaeppel's TASC Nov 2019 global seasonality finding (buy
end-October, sell end-April -- the classic "sell in May" 6-month hold)
across 18 country ETFs + SPY, Alvarez found the pattern shifted
post-2012: buying end-October and holding through end-JULY (a 10-month
hold) beat the classic 6-month split in 12/18 ETFs for 2012-2023 (vs only
4/18 for the classic split), attributed to shorter/milder post-2012 bear
markets from Fed intervention.

## Grid test summary (Step 6)

Grid: `entry_month` in {9,10,11} x `hold_months` in {6,8,9,10}, QQQ/SPY
(equity), BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3, 2019-2026.

- **Overall pass_fraction:** 0.215 (31/144)
- **By asset class:** equity 29/72 (0.403) vs crypto 2/72 (0.028) --
  crypto essentially fails outright.
- **By vol regime:** low 24/48 (0.500), mid 7/48 (0.146), high 0/48
  (0.000) -- the strategy's edge (a long-hold, buy-and-mostly-hold
  seasonal timing) evaporates entirely in high-vol conditions, unsurprising
  for a long-duration unconditional hold with no drawdown control.
- **Best cell:** SPY entry_month=10/hold_months=10, low-vol, Sharpe 2.615.
- **Worst cell:** SPY entry_month=9/hold_months=6, mid-vol, Sharpe -0.412.

## Single-config validation (Step 7)

Best full-sample config (entry_month=10, hold_months=10, i.e. buy end-Oct,
sell end-Aug of the following year):

| Symbol | Sharpe | MDD | TC-adj Sharpe | Trades |
|---|---|---|---|---|
| QQQ | 1.116 (PASS) | 0.328 (FAIL, thresh 0.25) | 1.111 (PASS) | 7 |
| SPY | 0.983 (FAIL) | 0.341 (FAIL) | 0.977 (PASS) | 7 |

Crypto full-sample Sharpe never exceeded 0.17 across all 3 configs tested
(entry_month=10/11, hold_months=9/10), with MDD 0.77-0.88 -- decisively
rejected.

## Decision: REJECT

QQQ clears the Sharpe threshold (1.116) but fails max-drawdown (0.328 vs
0.25 threshold) -- a long 10-month unconditional hold captures the full
2022 bear-market drawdown with no exit mechanism to avoid it. SPY fails
both Sharpe and MDD. Crypto decisively rejected. Unlike the source's own
framing (which measures relative performance vs the classic 6-month
split, not an absolute Sharpe/MDD acceptance bar), this repo's stricter
absolute thresholds are not met. A future rescue attempt could add a
trend/regime filter (e.g. skip the hold entirely if price is below its
200d SMA at entry, or add an early-exit stop) to address the MDD failure,
but that would depart materially from the source's own unconditional
calendar-only rule.

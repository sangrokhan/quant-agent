# Backtest Report: Slow RSI (SRSI) Oversold Reversal with Trend Filter (Apirine, TASC Apr/Jul 2015)

**Strategy file:** `strategies/2026-09-17_slow_rsi_oversold_trend_filter.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2015/07/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

Apirine's Slow RSI applies Wilder's RSI recursive net-change/total-change
smoothing to an EMA-smoothed price series (rather than raw close),
producing a double-smoothed 0-100 oscillator intended to reduce whipsaw.
This iteration's own trading rule (source disclosed the SRSI function/
indicator only, no explicit strategy): long entry when SRSI crosses above
`oversold` from below AND close>SMA(trend_window); exit on SRSI crossing
overbought, trend filter breaking, or a max_hold_days time-stop.

## Step 6 grid summary (oversold in {25,30,40} x trend_window in {50,100}, 3 vol terciles, equity+crypto, 72 cells)

- `pass_fraction`: 8/72 = 0.111
- `by_asset_class`: equity 5/36, crypto 3/36
- `by_vol_regime`: low 3/24, mid 2/24, high 3/24 (no strong regime concentration)
- `best_cell`: oversold=25/trend_window=100, SPY, high-vol, Sharpe 1.71
- `worst_cell`: oversold=30/trend_window=50, QQQ, mid-vol, Sharpe -0.76

## Full-sample validation at grid-best config (oversold=25, trend_window=100)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | FAIL (0.741) | PASS (1.197) |
| Max Drawdown | PASS (0.035) | PASS (0.019) |
| TC survival | PASS (0.715) | PASS (1.164) |
| Trades | 5 | 3 |

A broader local search (oversold in {20-40}, trend_window in {50-200},
max_hold_days in {10,20,30}) found only a marginal QQQ config (Sharpe
1.007, right at the threshold) with equally sparse trades. Both symbols'
"passing" configs have only 3-5 trades over 7.5 years -- far too few for a
statistically meaningful Sharpe estimate, and the marginal QQQ pass is not
a robust rescue.

## Decision

**Reject** (both QQQ and SPY produce too few trades (3-5) at any
config that clears the Sharpe threshold to be a credible signal; overall
grid pass_fraction 0.111 is low with no clear regime or asset-class
concentration explaining the passes as anything but noise). The
underlying double-smoothed SRSI oscillator moves too slowly to generate a
meaningful number of oversold-reversal signals combined with a trend
filter on this repo's daily-bar universe.

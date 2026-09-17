# Backtest Report: Rich Method (Triple-MA-Aligned Channel Breakout with Market Trend Filter, TASC Nov 2015/Jan 2016)

**Strategy file:** `strategies/2026-09-17_rich_method_triplema_channel.py`
**Source:** https://traders.com/Documentation/FEEDbk_docs/2016/01/TradersTips.html
(read this iteration via browser_exec after web_search DDGS backend errored;
direct traders.com archive URL navigation to a previously-unvisited month)

## Hypothesis

James and John Rich's "Simplify It" method combines: (1) a market-wide
2-day ROC-of-50-day-SMA trend filter (self-referential same-symbol proxy
here), (2) a triple-MA simultaneous alignment filter (close>50SMA,
20SMA>50SMA, 50SMA>200SMA), and (3) an average-high/low channel breakout
(8-day SMA of High/Low, not raw Donchian max/min) as the entry trigger.

## Step 6 grid summary (chan_length in {8,12,20} x fast_ma_length in {15,20,30}, 3 vol terciles, equity+crypto, 108 cells)

- `pass_fraction`: 20/108 = 0.185
- `by_asset_class`: equity 17/54, crypto 3/54
- `by_vol_regime`: low 18/36, mid 2/36, high 0/36
- `best_cell`: chan_length=8/fast_ma_length=20 (article default), SPY,
  low-vol, Sharpe 1.74 (single narrow tercile, not representative of
  full-sample performance)
- `worst_cell`: chan_length=20/fast_ma_length=15, BTC/USDT, low-vol, Sharpe -1.33

## Full-sample validation at article-default config (chan_length=8, fast_ma_length=20)

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | FAIL (0.351) | FAIL (0.335) |
| Max Drawdown | PASS (0.229) | PASS (0.159) |
| TC survival | FAIL (0.251) | FAIL (0.169) |
| Walk-forward | FAIL (1/4) | FAIL (2/4) |
| Trades | 56 | 60 |

A broader local search (chan_length in {5-20}, fast_ma_length in {15-30},
market_trend_ma_length in {30-75}) found NO configuration on either QQQ or
SPY that simultaneously clears Sharpe>=1.0 and MDD<=0.25 -- the grid's
apparent "best cell" was a low-vol-tercile-only artifact that does not
generalize to the full sample.

## Decision

**Reject** (QQQ and SPY both fail Sharpe/TC-survival/walk-forward
decisively at full sample; crypto fails even more decisively). The
self-referential same-symbol market-trend proxy (using the traded symbol
itself as its own "market trend" reference, since a genuine cross-symbol
SPY-as-market-proxy lookup isn't available in this repo's single-symbol
strategy interface) may weaken the filter's intended discriminating power
relative to the source's own design (which explicitly uses SPY as an
external market-trend reference even when trading a different symbol) --
worth revisiting with genuine cross-symbol data if this repo's interface
is extended to support it.

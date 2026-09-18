# 39-Period Slow Stochastic %K 50-Line Cross, OBV-Confirmed — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "The 'Last' Stochastic
Technique"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/the-last-stochastic-technique,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content, citing "The Encyclopedia of Technical Market
Indicators"): a long-period (39-bar) Stochastic %K crossing above its own
50 midline, confirmed by On-Balance Volume being above its own 30-day SMA,
produces a higher-quality trend-continuation signal than either indicator
alone. Long only while BOTH conditions hold; flat otherwise.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/the-last-stochastic-technique
(StockCharts.com ChartSchool).

## Grid summary (Step 6)

- Grid: stoch_window∈{20,39,60} × obv_sma_window∈{20,30,50}, symbols=
  {QQQ,SPY}×{BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to
  2026-09-01).
- 108 total cells, 44 passed (pass_fraction=0.41) — one of the broadest
  pass fractions of any strategy tested this cron trigger.
- by_asset_class: equity 26/54; crypto 18/54 (crypto shows real signal, not
  just noise, but see MDD failure below).
- by_vol_regime: low 27/36, mid 17/36, high 0/36 — same universal high-vol
  regime failure pattern as most trend-following strategies in this repo.
- Best cell: ETH/USDT stoch_window=60/obv_sma_window=30, mid-vol Sharpe=2.57.

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Best config | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel.std) |
|---|---|---|---|---|---|---|
| QQQ | stoch_window=50, obv_sma_window=30 | 1.379 (PASS) | 0.149 (PASS) | 1.188 (PASS) | 4/4=1.00 (PASS) | 0.106 (PASS) |
| SPY | stoch_window=30, obv_sma_window=30 | 1.050 (PASS) | 0.150 (PASS) | 0.786 (PASS) | 3/4=0.75 (PASS) | 0.106 (PASS) |
| BTC/USDT | stoch_window=39, obv_sma_window=20 | 1.340 (PASS) | 0.465 (FAIL) | 1.283 (PASS) | 4/4=1.00 (PASS) | 0.078 (PASS) |
| ETH/USDT | stoch_window=60, obv_sma_window=30 | 1.225 (PASS) | 0.587 (FAIL) | 1.193 (PASS) | 4/4=1.00 (PASS) | 0.090 (PASS) |

## Decision: ACCEPT (QQQ and SPY)

Both equity symbols clear all 5 validators. QQQ is especially strong (Sharpe
1.379, MDD only 14.9%, all validators pass comfortably). SPY passes with a
tighter margin (walk-forward exactly at the 0.75 threshold, 3/4 splits
positive) but still a clean accept. Crypto (BTC/USDT, ETH/USDT) shows
genuinely strong Sharpe (1.22-1.34, low parameter sensitivity, perfect
walk-forward) but decisively fails max drawdown (46.5%/58.7% vs 25% cap) --
the strategy stays long through crypto's much larger multi-month drawdown
episodes since the exit condition (either %K<50 or OBV<its SMA) reacts
comparatively slowly to sudden severe reversals at this asset class's scale.
Consistent with dozens of other strategies in this repo, the signal
generalizes directionally to crypto but needs a leverage-cap-aware or
ATR-based risk overlay to control crypto drawdown -- not attempted this
iteration, a candidate for a future targeted retune.

This strategy is added to `strategies/` as a live QQQ+SPY strategy.

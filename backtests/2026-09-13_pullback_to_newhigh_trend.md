# Backtest Report: Pullback-to-New-High Trend Continuation (2026-09-13)

## Hypothesis
Per https://www.tradequantixnewsletter.com/p/momentum-mini-portfolio-development-302
(TradeQuantiX "USA Pullback Momentum" mini-portfolio piece, read via browser_exec),
a cross-sectional momentum system only buys stocks AFTER a pullback of X% off
their highs (author settled on 15%, tested 0-25%), and the author's own
isolated pullback sub-study exits at a new N-day high (trend resumed) rather
than reverting to a moving average. This repo adapted the idea to a
single-instrument absolute-trend version: long only when in an uptrend
(close > SMA(trend_window)) AND currently pulled back `pullback_pct` off the
rolling `high_lookback`-day high; exit on a new `exit_lookback`-day high, a
trailing stop, or a time-stop.

Source URL: https://www.tradequantixnewsletter.com/p/momentum-mini-portfolio-development-302

## Strategy file
strategies/2026-09-13_pullback_to_newhigh_trend.py

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, pullback_pct=[0.10,0.15,0.20] x exit_lookback=[40,60,90], vol_regime_splits=3, 2018-2026)

- total_cells: 108, passed_cells: 12, pass_fraction: 0.111
- by_asset_class: equity 12/54 pass, crypto 0/54 (decisive fail)
- by_vol_regime: low 0/36, mid 12/36 (all passes concentrated in mid-vol), high 0/36
- best_cell: QQQ, pullback_pct=0.20/exit_lookback=90, mid-vol, Sharpe 2.37
- worst_cell: QQQ, pullback_pct=0.20/exit_lookback=40, low-vol, Sharpe -0.97

Interpretation: only works in mid-volatility equity regimes; crypto fails
entirely; low/high vol regimes fail on equity too. Not a broad edge.

## Step 7 single-config validators (best grid config: pullback_pct=0.20, exit_lookback=90, full sample 2018-2026)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe | 0.927 FAIL | 0.238 FAIL | >= 1.0 |
| Max Drawdown | 18.7% PASS | 7.6% PASS | <= 25% |
| TC-survival (10bps/trade) | 0.907 PASS (12 trades) | 0.229 FAIL (3 trades) | >= 0.5 |
| Walk-forward (4 equal slices) | 4/4 PASS | 4/4 PASS | >= 0.75 |
| Parameter sensitivity (rel. std) | 0.430 PASS | 0.374 PASS | <= 0.5 |

Full-sample Sharpe fails on both QQQ and SPY when using the whole
2018-2026 window (the grid's mid-vol-only cherry-picked cell looked
strong, but full-sample dilutes it with low/high-vol losses, consistent
with the grid's vol-regime breakdown). SPY additionally has too few trades
(3) for a meaningful TC-survival read and fails it outright.

## Decision: REJECTED

Primary validator (Sharpe >= 1.0) fails on both equity symbols at
full-sample; the grid's own vol-regime breakdown shows the edge (where it
exists at all) is confined to mid-vol equity regimes only, and crypto is a
decisive 0/54. Not accepted.

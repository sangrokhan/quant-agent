# CCI(14) Trend-Continuation Breakout — Backtest Report

**Hypothesis:** Per TradeAlgo's CCI trading-guide (search snippet; direct
page fetch via browser_exec rendered near-empty, 656 chars, JS-lazy-loaded
SPA shell) trend-continuation strategy: enter long when CCI crosses above
+100 from below (strong momentum breakout, opposite economic thesis from
the oversold mean-reversion CCI variant already rejected at
2026-09-04-024). Hold while CCI stays above zero. Exit when CCI drops below
zero.

Source: https://www.tradealgo.com/trading-guides/technical-analysis/commodity-channel-index-cci-how-to-identify-cyclical-price-patterns
(search snippet text used; page body itself did not render via browser_exec).
Cross-checked qualitative CCI framing against
https://pictureperfectportfolios.com/how-to-use-the-commodity-channel-index-cci-in-trading/
(long-form explainer, no more concrete numeric rule found there).

## Step 6 — Grid test (cci_window x entry_threshold x asset class x vol regime)

Grid: `cci_window` in [14, 20, 30], `entry_threshold` in [100, 150],
symbols equity=[QQQ, SPY], crypto=[BTC/USDT, ETH/USDT], vol_regime_splits=3
(low/mid/high realized-vol terciles). 72 cells total.

- **pass_fraction: 0.236 (17/72)**
- by_asset_class: equity 17/36 passed; **crypto 0/36 passed** (decisive reject)
- by_vol_regime: low 12/24; mid 5/24; high 0/24 (classic pattern seen
  repeatedly in this repo: trend-following signals concentrate their edge
  in low-vol regimes, fail in high-vol chop)
- best_cell: QQQ, cci_window=14, entry_threshold=100, vol_regime=low,
  Sharpe 2.63
- worst_cell: QQQ, cci_window=30, entry_threshold=150, vol_regime=high,
  Sharpe -0.58

## Step 7 — Single-config validation (best full-sample config: QQQ, cci_window=14, entry_threshold=100)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.158 | 1.0 |
| Max drawdown | ✅ | 0.237 | 0.25 |
| Transaction cost survival (10bps/trade, 66 trades) | ✅ | 1.062 (net Sharpe) | 0.5 |
| Walk-forward (4 splits, manual date-slice; vectorbt splitter API broken as noted in prior entries) | ✅ | 0.75 (3/4 splits positive: 2.49, -0.09, 1.67, 0.69) | 0.75 |
| Parameter sensitivity (6-combo QQQ grid, rel. std) | ✅ | 0.0915 | 0.5 |

**QQQ: all 5 validators pass — accepted.**

### SPY near-miss (best SPY config: cci_window=20, entry_threshold=100)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.990 | 1.0 |
| Max drawdown | ✅ | 0.127 | 0.25 |
| Transaction cost survival (53 trades) | ✅ | 0.886 | 0.5 |

SPY misses Sharpe by 0.01 — essentially a coin-flip miss, not a decisive
rejection, but not separately re-run for walk-forward/param-sensitivity
since it doesn't clear the primary bar.

### Crypto (BTC/USDT, ETH/USDT)

0/36 grid cells passed across all param x vol-regime combos — decisively
rejected, consistent with most trend/momentum-oscillator strategies tested
in this repo underperforming on crypto's noisier realized-vol profile.

## Outcome

**Accepted for QQQ** (cci_window=14, entry_threshold=100, exit_threshold=0).
SPY logged as a near-miss (Sharpe 0.99, one basis point of Sharpe shy of the
threshold). Crypto rejected decisively.

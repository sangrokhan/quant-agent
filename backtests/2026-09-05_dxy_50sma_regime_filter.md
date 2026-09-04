# DXY 50-day SMA Regime Filter — Backtest Report (REJECTED)

**Hypothesis:** DXY (US Dollar Index) trading below its 50-day SMA marks a
bullish/risk-on equity regime (long SPY/QQQ); DXY at/above its 50-day SMA
marks a bearish/protective regime (flat). Source: Google AI-overview summary
citing TradingView/TIOmarkets/RoboForex material on DXY-filtered SPY/QQQ
strategies (retrieved via `https://www.google.com/search?q=McClellan+Oscillator...`
browser fallback, since the query auto-redirected to a DXY/SPY AI overview);
background on DXY trend strategies also cross-checked at
https://www.quantifiedstrategies.com/us-dollar-trading-strategy/ (paywalled
beyond intro — full Python code member-gated, only the general trend-strategy
framing was usable).

## Single-config validators (SPY, sma_window=50, 2019-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.744 | >= 1.0 | **FAIL** |
| Max drawdown | 20.7% | <= 25% | pass |
| Transaction cost survival (10bps/trade, 139 trades) | net Sharpe 0.530 | >= 0.5 | pass |
| Parameter sensitivity (sma_window in {20,50,100}) | rel std 0.074 | <= 0.5 | pass |
| Walk-forward | not run | — | skipped: pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt (see prior reports, e.g. 2026-09-05_yield_curve_uninvert_bear.md) |

## Grid test summary (sma_window in {20,50,100} x equity{QQQ,SPY} x crypto{BTC/USDT,ETH/USDT} x vol tercile)

- total_cells: 36, passed_cells: 7, **pass_fraction: 0.194**
- by_asset_class: equity 7/18 passed; **crypto 0/18 passed** (as expected —
  falsification check, dollar-liquidity regime filter has no claimed edge on
  crypto)
- by_vol_regime: low 6/12, mid 1/12, high 0/12 — only works (if at all) in
  low-realized-vol regimes, breaks down entirely in high-vol regimes
- best cell: SPY, sma_window=50, low-vol regime, Sharpe 3.07
- worst cell: SPY, sma_window=50, mid-vol regime, Sharpe -0.37

## Verdict: REJECTED

Primary-config Sharpe (0.74) misses the 1.0 threshold on the full SPY
sample despite passing MDD, tx-cost-survival, and parameter sensitivity.
The grid confirms the strategy's edge is narrow: it only clears validator
bars in low-vol regimes (mostly on SPY specifically), fails on crypto
entirely (expected), and fails outright in mid/high-vol regimes — i.e. the
regime filter looks attractive cherry-picked to calm markets but doesn't
hold up broadly. Not accepted as a live strategy in `strategies/`.

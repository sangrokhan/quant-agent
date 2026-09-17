# Backtest Report: Donchian Channel Middle-Line Slope Trend-Following

**Strategy file:** `strategies/2026-09-18_donchian_midline_slope_trend.py`
**Hypothesis id:** 2026-09-18-004
**Source:** https://traders.com/Documentation/FEEDbk_docs/2023/08/TradersTips.html (TASC Aug 2023, "Using Price Channels", Stella Osoba; MetaQuotes/MQL5 slope-coloring extension disclosed in the same Traders' Tips page)

## Hypothesis

Donchian channel middle line = (Highest(High,N) + Lowest(Low,N))/2. The
article's MQL5 implementation extends the plain channel with a
color-changing middle line (green when rising, red when falling) and
buy/sell arrows fired on the slope flip. This is distinct from every
Donchian-midline strategy already tested in this repo (all used the
midline as a pullback/mean-reversion reference level) -- this iteration
instead trades the midline's own slope direction as a standalone trend
signal: long on slope flip from falling to rising, exit on flip back,
gated by an SMA(trend_window) uptrend filter.

## Grid Test Summary (Step 6)

Grid: `channel_window` in {15,20,30}, `slope_lookback` in {2,3,5},
`trend_window` in {50,100}, symbols equity {QQQ, SPY} + crypto {BTC/USDT,
ETH/USDT}, vol_regime_splits=3.

- total_cells: 216, passed_cells: 77, **pass_fraction: 0.356**
- by_asset_class: equity 55/108, crypto 22/108 (edge holds in both, weaker crypto)
- by_vol_regime: low 52/72, mid 23/72, high 2/72 (edge concentrated low-vol)
- best_cell: SPY low-vol, channel_window=20/slope_lookback=2/trend_window=50, Sharpe 2.56
- worst_cell: QQQ high-vol, channel_window=15/slope_lookback=3/trend_window=100, Sharpe -0.72

## Single-Config Validation (Step 7)

Config: `channel_window=20, slope_lookback=2, trend_window=50`.

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity | Verdict |
|--------|--------|-----|------------------------|--------------|--------------------|---------|
| QQQ    | 1.383  | 0.124 | 1.105                 | 1.0 (4/4)    | 0.230              | **ACCEPT** |
| SPY    | 0.925  | 0.185 | 0.572                 | 1.0 (4/4)    | 0.306              | REJECT (Sharpe near-miss) |
| BTC/USDT | 0.801 | 0.497 | 0.742                | 1.0 (4/4)    | 0.178              | REJECT (decisive MDD fail) |
| ETH/USDT | 0.710 | 0.697 | 0.664                | 0.75 (3/4)   | 0.217              | REJECT (decisive Sharpe+MDD fail) |

Crypto's frequent-trading (~310 trades) combined with much larger drawdowns
(MDD 0.50-0.70) suggests this trend-flip signal is too noisy/whipsaw-prone on
crypto's volatility profile without a leverage cap or additional filter --
consistent with several other trend-flip strategies in this repo failing
crypto for the same reason. Not pursued further (leverage-cap rescue) this
iteration given the decisive scale of the MDD miss.

## Decision (Step 8)

**Accepted for QQQ only**, all 5 validators pass. SPY, BTC/USDT, ETH/USDT
rejected this iteration.

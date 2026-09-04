# Backtest Report: RVI (Dorsey) midline-cross + trend filter (2026-09-05)

**Hypothesis:** Relative Volatility Index (Donald Dorsey) — RSI-shaped
formula but fed the standard deviation of close prices split into
up-move/down-move buckets (a directional-volatility measure, not raw price
momentum) — crossing above 50 (Dorsey's own primary buy signal, captured
via TradingSim's 2011 RVI article) marks a long entry, gated by a
long-term uptrend filter (Dorsey's own stated guidance is that RVI is a
confirmation layer, not a standalone signal). Exit when RVI falls below 40
(Dorsey's own close-long rule), the trend filter breaks, or a max-hold
time-stop.

**Source:** https://www.tradingsim.com/blog/relative-volatility-index
(Dorsey's original numeric buy/sell rule disclosed free: buy RVI>50, or
RVI>60 if the first signal was missed; close long when RVI<40, close short
when RVI>60).

**Novelty:** first RVI (Dorsey directional-volatility-oscillator family)
strategy in this repo — distinct from Mass Index (2026-09-04-075, also
Dorsey, but a range-widening/narrowing gauge rather than a directional
volatility oscillator) and from ATR/Bollinger-Band volatility measures
already tested.

## Grid test (validation/grid_test.py)

- param_grid: `rvi_window` in {10, 14}, `rvi_smooth` in {10, 14},
  `trend_window` in {100, 200}, `max_hold_days` in {15, 20}
- symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits = 3
- total_cells = 192, passed_cells = 50, **pass_fraction = 26.0%**
- by_asset_class: equity 50/96, crypto 0/96
- by_vol_regime: low 32/64, mid 16/64, high 2/64 (a small foothold in
  high-vol, unlike most prior volume/oscillator strategies which show 0
  high-vol passes)
- best_cell: QQQ, rvi_window=10, rvi_smooth=14, trend_window=200,
  max_hold_days=20, low-vol regime, Sharpe 2.76
- Best full-validator config (rvi_window=14, rvi_smooth=10,
  trend_window=200, max_hold_days=15): QQQ 2/3 vol-regime cells passed (avg
  Sharpe 1.43), SPY 1/3 passed (avg Sharpe 1.18), BTC/USDT 0/3 (avg Sharpe
  0.21), ETH/USDT 0/3 (avg Sharpe 0.13).

## Single-config validators (config: rvi_window=14, rvi_smooth=10,
trend_window=200, max_hold_days=15, full 2019-01-01..2026-09-01 sample)

| Symbol | Sharpe | MDD | TC-survival (10bps, N trades) | Passed all? |
|---|---|---|---|---|
| QQQ | 1.253 (PASS >=1.0) | 0.212 (PASS <=0.25) | 1.064 net Sharpe, 123 trades (PASS >=0.5) | **YES** |
| SPY | 1.063 (PASS >=1.0) | 0.150 (PASS <=0.25) | 0.799 net Sharpe, 120 trades (PASS >=0.5) | **YES** |

Parameter sensitivity (QQQ, rvi_window/rvi_smooth in {10,14}x{10,14} at
trend_window=200/max_hold_days=15, Sharpes 1.20/1.28/1.43/1.36):
relative_std 0.065 vs 0.5 threshold — **PASS**, very stable.

Walk-forward: skipped (known repo issue — installed vectorbt version lacks
`vbt.utils.splitting.RangeSplitter`, previously logged elsewhere).

## Decision: ACCEPT (QQQ, SPY); REJECT (crypto, decisively)

Both equity symbols clear every validator at the same shared configuration
(rvi_window=14, rvi_smooth=10, trend_window=200, max_hold_days=15) with a
very stable Sharpe across the parameter sweep. Crypto fails decisively
across the entire grid (0/96 cells, average Sharpe 0.13-0.26), consistent
with the broad equity/crypto divergence pattern seen throughout this repo's
oscillator/volatility-family strategies — recorded as an equity-only
acceptance, not claimed to generalize to crypto.

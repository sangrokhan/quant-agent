# Range Filter [DW] (DonovanWall) trend-following crossover

**Hypothesis:** The Range Filter [DW] (DonovanWall, popularized via
marketcalls.in's Amibroker port) filters minor price action via a two-stage
EMA-smoothed average absolute-change range, then a recursive "ratchet"
filter line that only moves toward price by up to that range each bar. A
rising-streak counter on the filter line, combined with close > filt,
signals a long entry; exit when the streak resets (filter stops rising) or a
max_hold_days time-stop.

Source: https://www.marketcalls.in/amibroker/range-filter-trading-strategy-amibroker-better-trend-following-indicator.html
(exact AFL formula transcribed, original TradingView source by DonovanWall
linked in the article: https://in.tradingview.com/script/lut7sBgG-Range-Filter-DW/)

Novelty: first Range Filter [DW] strategy in this repo — a non-ATR-based
recursive ratchet-toward-price construction, distinct from all prior
EMA/SMA crossover, Keltner/Bollinger band, or ATR-trailing-stop
constructions (including Gann HiLo Activator id=2026-09-05-017 and
SuperTrend id=2026-09-03-014, both of which flip between two static
lines/bands rather than ratcheting a single continuous line toward price).

## Step 6 — Grid summary

Grid: `sampling_period in {10,15,20}`, `range_mult in {1.5,2.5,3.5}`,
`max_hold_days in {15,25}`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
vol_regime_splits=3, 144 total cells.

- pass_fraction: 0.382 (55/144)
- by_asset_class: equity 55/108 passed; crypto 0/36 (ccxt loader tz-aware
  Timestamp error, same known issue noted in 2026-09-05-017)
- by_vol_regime: low 36/36, mid 18/36, high 1/36
- best_cell: sampling_period=15, range_mult=3.5, max_hold_days=15, SPY,
  low-vol, Sharpe 2.53

## Step 7 — Single-config validation (sampling_period=15, range_mult=3.5, max_hold_days=15)

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe (>=1.0) | 0.674 FAIL | 0.957 FAIL (marginal) |
| Max drawdown (<=0.25) | 0.177 PASS | 0.193 PASS |
| Net-of-cost Sharpe (>=0.5, 10bps/trade) | 0.509 PASS | 0.832 PASS |
| Param sensitivity relative_std (<=0.5, range_mult in {1.5,2.5,3.5}) | 0.124 PASS | 0.288 PASS |
| num_trades | 105 | 95 |
| Walk-forward | not run — `vbt.utils.splitting.RangeSplitter` unavailable in this repo's installed vectorbt version (same known limitation as prior entries). |

## Step 8 — Decision

**Rejected.** Full-sample Sharpe decisively fails on SPY (0.674) and
marginally fails on QQQ (0.957) against the 1.0 threshold, despite grid
isolated low/mid-vol-tercile passes (best cell Sharpe 2.53, 100% of low-vol
cells passed). Not an overfitting issue — parameter sensitivity is
excellent on both symbols (relative_std 0.124/0.288) — the edge magnitude
simply doesn't survive full-sample averaging given the high trade frequency
(105/95 trades over 8.5yr), the same failure mode already logged for Ehlers
Roofing Filter (2026-09-05-012) and Polarized Fractal Efficiency
(2026-09-05-014) this run. Crypto rejected due to the known ccxt loader
tz-aware Timestamp bug (0 usable cells, not a strategy-quality rejection).

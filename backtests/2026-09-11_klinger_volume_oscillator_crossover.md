# Klinger Volume Oscillator (KVO) Signal-Line Crossover, Trend-Gated — Backtest Report

**Date:** 2026-09-11
**Strategy file:** `strategies/2026-09-11_klinger_volume_oscillator_crossover.py`
**Sources:**
- https://lightningchart.com/blog/trader/klinger-volume-oscillator/
- https://www.investopedia.com/terms/k/klingeroscillator.asp

## Hypothesis

Klinger's Volume Force (VF) combines volume, high-low range, and a +1/-1
trend-direction sign into a "volume pressure" measure; KO = 34-period EMA(VF)
− 55-period EMA(VF), smoothed by a signal line = 13-period EMA(KO). Per both
sources: bullish crossover (KO > signal) = buy signal (volume accumulation
accelerating), bearish crossover = sell/exit. Gated here with a trend filter
(close > SMA(trend_window)) and a max-hold time-stop.

## Grid test summary (Step 6)

`scripts/run_grid_klinger.py` — param grid `signal_period∈{9,13,21}`,
`trend_window∈{50,100}`, `max_hold_days=60` × symbols `{QQQ,SPY,BTC/USDT,ETH/USDT}`
× 3 vol-regime terciles (72 total cells).

- **pass_fraction: 0.181** (13/72)
- **by_asset_class:** equity 13/36 passed, **crypto 0/36 passed** (decisive rejection on crypto)
- **by_vol_regime:** low 12/24, mid 1/24, high 0/24 (edge almost entirely confined to low-vol)
- **best_cell:** QQQ, signal_period=13/trend_window=100/max_hold_days=60, low-vol, Sharpe 2.17
- **worst_cell:** SPY, same params, high-vol, Sharpe -0.41

## Single-config validators (Step 7) — best grid config (signal_period=13, trend_window=100, max_hold_days=60), full sample 2010-2026

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward (4-split) | Param sensitivity (rel std) | # trades |
|---|---|---|---|---|---|---|
| QQQ | **0.527 (FAIL, thr 1.0)** | **0.313 (FAIL, thr 0.25)** | **0.257 (FAIL, thr 0.5)** | 1.0 (pass) | 0.184 (pass) | 316 |
| SPY | **0.514 (FAIL, thr 1.0)** | 0.178 (pass) | **0.175 (FAIL, thr 0.5)** | 0.75 (pass) | 0.123 (pass) | 319 |

The strategy generates a very high number of trades (~316-319 over 2010-2026,
roughly one every 2 weeks) — the crossover-based entry/exit is much noisier
than the low-vol-tercile-only grid cell (which used a shorter, favorable
sub-window) suggested. On the full sample, transaction costs (10bps/trade)
erode Sharpe from already-sub-1.0 gross values down to 0.17-0.26 net,
decisively failing the cost-survival check.

## Decision: REJECTED

Both QQQ and SPY fail the Sharpe threshold and the transaction-cost-survival
check on the full 2010-2026 sample; QQQ additionally fails max drawdown. The
grid's apparently-strong low-vol-regime cells (best_cell Sharpe 2.17) do not
generalize to the full-period, all-regime picture once trade frequency and
realistic transaction costs are accounted for — the KVO signal-line crossover
fires too often (noisy oscillator, frequent whipsaws) for a 10bps-per-trade
cost assumption to survive. Crypto is decisively rejected across the whole
grid (0/36 cells).

Possible future revisit: widen the signal_period/short/long EMA spans further
(reduce whipsaw frequency) or add a minimum-KO-magnitude threshold before
allowing a crossover to count as a valid signal (avoid trading small
noise-level crosses near zero).

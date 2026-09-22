# Ehlers Roofing Filter Crossover — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ehlers_roofing_filter_crossover.py`
**Status:** REJECTED

## Hypothesis

Per John F. Ehlers' "Cycle Analytics for Traders" (2013, ch.7), the Roofing
Filter combines a two-pole high-pass filter with a Super Smoother low-pass
filter to isolate cyclic price components between two critical periods. Per
the TradingView "[blackcat] L2 Ehlers Roofing Filter Indicator" description
(source: https://kr.tradingview.com/scripts/roofingfilter/, read via
browser_exec this iteration — web_search DDGS backend intermittently
TLS-erroring on several queries this session): "the ideal time to buy is
when the cycle is at a trough... flagged by the filter crossing itself
delayed by one bar." Implemented as a long-only strategy: Filt (fast
roofing-filter line) crossing above its own 1-bar-lagged value (Trigger)
signals entry, gated by an SMA(trend_window) uptrend filter; exit on the
reverse crossover, trend flip, or a `max_hold_days` time-stop.

First Ehlers Roofing Filter crossover strategy in this repo (0 prior
matches for "Roofing Filter" in `strategies_index.jsonl`) — distinct from
the repo's already-saturated plain Super Smoother, Fisher Transform, and
other Ehlers-family entries.

## Grid test summary (Step 6)

`run_strategy_grid`: `hp_period` in {36,48,60}, `lp_period` in {8,10,14},
`trend_window` in {50,100}; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto); `vol_regime_splits=3`.

- **total_cells:** 216, **passed_cells:** 62, **pass_fraction:** 0.287
- **by_asset_class:** equity 34/108 (0.315), crypto 28/108 (0.259)
- **by_vol_regime:** low 45/72 (0.625), mid 17/72 (0.236), **high 0/72 (0.000)**
- **best_cell:** hp_period=60, lp_period=14, trend_window=50 — ETH/USDT, mid-vol, Sharpe 2.65
- **worst_cell:** hp_period=36, lp_period=14, trend_window=50 — QQQ, high-vol, Sharpe -1.17

Clear pattern: the strategy only works in low-volatility regimes and
collapses entirely (0/72 passes) in high-vol regimes — the cyclic
roofing-filter signal appears to be swamped by noise/large moves exactly
when volatility spikes.

## Single-config validation (Step 7) — best grid config (hp=60, lp=14, trend_window=50)

| Validator | QQQ (equity) | ETH/USDT (crypto, 1d bars) | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.183 — **FAIL** | 0.866 — **FAIL** | ≥ 1.0 |
| Max drawdown | 0.141 — PASS | 0.627 — **FAIL** | ≤ 0.25 |
| TC survival (10bps/trade, 92-93 trades) | 0.007 — **FAIL** | 0.829 — PASS | ≥ 0.5 net Sharpe |
| Walk-forward (manual 4-split) | 0.75 (3/4) — PASS | 0.75 (3/4) — PASS | ≥ 0.75 |
| Parameter sensitivity (hp×lp 3×3 grid) | rel_std 0.676 — **FAIL** | rel_std 0.084 — PASS | ≤ 0.5 |

Neither symbol clears all 5 validators at the grid's best config: QQQ fails
Sharpe, TC-survival, and parameter sensitivity; ETH/USDT fails Sharpe and
max-drawdown (a 62.7% MDD on crypto is decisive).

## Decision

**REJECTED.** No config in the grid clears all validators on either asset
class. The strategy shows a real but narrow edge confined to low-vol
regimes (62.5% grid pass rate there vs 0% in high-vol) — this narrow scope
plus the crypto MDD/equity Sharpe failures at the best-cell config make it
not viable as currently constructed. A future rescue attempt could try
gating out of high-vol regimes explicitly (rather than relying on the trend
filter alone) or reframing Filt/Trigger divergence as a continuous sizing
dial per this repo's established binary-to-continuous rescue pattern.

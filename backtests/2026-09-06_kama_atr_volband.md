# Backtest Report: KAMA + ATR Volatility-Band Trend Following

**Strategy file:** `strategies/2026-09-06_kama_atr_volband.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-181

## Hypothesis

Kaufman's Adaptive Moving Average (KAMA) adjusts its smoothing constant via
an Efficiency Ratio, hugging price during efficient trends and flattening
during noisy/choppy conditions. Per a Google AI-overview synthesis of a
Medium (David Borst) "Kaufman Adaptive Moving Average and ATR Long Position
Strategy" write-up: long entry when close crosses above KAMA AND ATR-as-%-
of-price is inside a normal volatility band `[atr_min_pct, atr_max_pct]`
(avoiding both dead-flat chop and already-blown-out volatility spikes); exit
when close crosses below KAMA OR ATR% spikes above `atr_exit_pct`, or a
`max_hold_days` time-stop.

**Source:** Google AI-overview synthesis of Medium/David Borst "Kaufman
Adaptive Moving Average and ATR Long Position Strategy" (fetched via
browser_exec Google search fallback after `web_search` returned no results
for the KAMA query and `quantifiedstrategies.com/adaptive-moving-average-trading-strategy/`
404'd). First KAMA strategy in this repo.

## Step 6 grid summary (`kama_grid_summary.json`)

Param grid: `fast_sc_period in {2,3}` x `atr_max_pct in {0.03, 0.05}` (fixed
`er_window=10, slow_sc_period=30, atr_window=14, atr_min_pct=0.005,
atr_exit_pct=0.06, max_hold_days=40`), symbols `{equity: [QQQ, SPY], crypto:
[BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.271** (13/48 cells, min_sharpe=1.0, max_allowed_mdd=0.25)
- **by_asset_class:** equity 13/24 passed; **crypto 0/24 passed** (fails
  decisively on both BTC/USDT and ETH/USDT across all vol regimes/params)
- **by_vol_regime:** low 8/16, mid 4/16, high 1/16 (clearly concentrated in
  low-vol regime; the strategy is essentially a low-vol trend-follower)
- **best_cell:** `fast_sc_period=3, atr_max_pct=0.05`, equity/SPY/low-vol,
  Sharpe 2.40
- **worst_cell:** `fast_sc_period=2, atr_max_pct=0.05`, equity/QQQ/high-vol,
  Sharpe -0.71

## Step 7 single-config validators (best config: SPY, `fast_sc_period=3,
atr_max_pct=0.05`, full sample 2018-2026-09)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | 0.894 | ≥ 1.0 |
| max_drawdown | ✅ | 0.165 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 109 trades) | ✅ | net Sharpe 0.707 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ✅ | 4/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity (4-cell grid: fast_sc_period x atr_max_pct, SPY) | ✅ | relative std 0.111 | ≤ 0.5 |

## Decision: **REJECT**

Full-sample Sharpe (0.894) misses the 1.0 threshold, despite passing every
other validator and despite the grid's best individual cell (low-vol regime
only) showing a strong Sharpe of 2.40. This is a **near-miss**: the grid
breakdown shows the edge is real but concentrated almost entirely in
low-volatility regimes (8/16 low-vol cells passed vs only 1/16 high-vol),
so the unconditional full-sample average gets dragged down by high-vol
periods where the ATR band doesn't fully filter out the KAMA-crossover
whipsaws. Also decisively fails on crypto (0/24) — KAMA's efficiency-ratio
smoothing does not appear to add value over 24/7 crypto's continuous noise
profile at these parameters.

**Worth revisiting:** a future iteration could add an explicit low-vol
regime gate (similar to `2026-09-03_bb_meanrev_qqq_volregime.py`'s realized-
vol-vs-median approach) on top of the KAMA/ATR-band entry, restricting
trading to the low-vol tercile outright rather than relying on the ATR band
alone to do that filtering — the grid data suggests this could push the
full-sample Sharpe of the low-vol-restricted variant well above 1.0.

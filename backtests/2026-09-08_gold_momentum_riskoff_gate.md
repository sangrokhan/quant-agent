# Backtest Report: Gold-Momentum Risk-Off Gate (defensive-asset early-warning filter)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_gold_momentum_riskoff_gate.py`
**Source:** Thomas Carlson, "Defense First: A Multi-Asset Tactical Model
for Adaptive Downside Protection" (2025), summarized at
https://www.quantitativo.com/p/from-defense-to-offense-a-tactical (read
via browser_exec after direct navigation from the Quantitativo archive
page).

## Hypothesis

The source's TAA model ranks defensive assets (TLT, GLD, DBC, UUP) monthly
by multi-timeframe momentum and rotates among them, falling back to equity
only when defenses are weak. Adapted here as a single-edge risk-off gate:
go flat on the primary equity/crypto asset whenever GOLD (GLD) itself shows
strong positive absolute momentum (flight-to-safety/monetary-instability
warning), layered on top of the primary's own SMA trend filter.

## Grid test summary (Step 6)

`param_grid={"trend_window":[50,100], "gold_lookback":[21,63], "gold_threshold":[0.03,0.05]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 96, **passed:** 17, **pass_fraction: 0.177**
- **by_asset_class:** equity 17/48; crypto 0/48 (decisive reject — GLD's
  momentum has no clear cross-asset link to crypto majors)
- **by_vol_regime:** low 16/32, mid 0/32, high 1/32 — nearly all passes in
  low-vol
- **best_cell:** QQQ, trend_window=50, gold_lookback=21, gold_threshold=0.03,
  low-vol regime, Sharpe 3.27; the SAME config's high-vol cell for the same
  symbol is Sharpe -0.38 (worst cell)

## Single-config validation (Step 7): trend_window=50, gold_lookback=21, gold_threshold=0.03

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.982 (**FAIL**, borderline) | 0.848 (**FAIL**) | >= 1.0 |
| Max drawdown | 0.186 (PASS) | 0.265 (**FAIL**) | <= 0.25 |
| TC survival (5bps/trade) | 0.833 (PASS, 186 trades) | 0.638 (PASS, 196 trades) | >= 0.5 |
| Walk-forward (4 manual chunks) | 1.0 (PASS) | 1.0 (PASS) | >= 0.75 |
| Parameter sensitivity (relative_std, 8-combo grid) | 0.292 (PASS) | 0.094 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug.)

## Decision: REJECT

Sharpe misses the bar on both QQQ (0.982, borderline) and SPY (0.848); SPY
also fails MDD (0.265 vs 0.25). Despite passing walk-forward and parameter
sensitivity comfortably on both, the gold risk-off gate's frequent
false-positive flags (186-196 trades over the sample -- a high trade count
for a supposedly rare "crisis warning" signal) erode returns via whipsaw
without meaningfully improving drawdown protection on SPY. The grid
confirms the edge is confined to low-vol regimes (only 1/32 high-vol cells
passed anywhere), and the same exact best-cell parameters swing from
Sharpe +3.27 (low-vol) to -0.38 (high-vol) on the identical QQQ series --
the gold-momentum signal is not a reliable regime-agnostic circuit-breaker
as hypothesized. Crypto rejected decisively (0/48). Worth revisiting: a
higher gold_threshold (rarer, more decisive gold spikes only) or requiring
gold momentum to be sustained over multiple periods before triggering
might reduce the whipsaw-driven Sharpe drag -- a candidate for a future
iteration.

# CUSUM Filter Trend-Event Entry (2026-09-10)

**Hypothesis**: Per https://github.com/muMAJJI/Trading---CUSUM-FILTER (README
on Lopez de Prado's symmetric CUSUM filter, "Advances in Financial Machine
Learning"): track two running cumulative sums of daily log-returns (S+
accumulates only positive deviations, resets on excursion below 0; S- is the
mirror). A trend event fires when S+ crosses an adaptive threshold h (=
h_mult * rolling realized vol), signalling a *sustained* run of same-sign
returns rather than one noisy spike. Adapted as a single-asset long-only
entry: long on a positive CUSUM event while close > SMA(200); exit on a
negative CUSUM event or a max_hold_days time-stop.

First CUSUM-filter-family strategy in this repo — distinct from all prior
regime-classification indicators (Hurst, variance ratio, autocorrelation
regime, HMM) since CUSUM flags discrete threshold-crossing events of
accumulated directional drift rather than an ongoing state.

**Grid** (`scripts/run_iter_cusum_filter.py`): `vol_window=[20,40]`,
`h_mult=[3.0,4.0,5.0]`, `max_hold_days=[30]`, equity (QQQ, SPY) x crypto
(BTC/USDT, ETH/USDT), vol_regime_splits=3, 2018-01-01 to 2026-09-01.

- total_cells=72, passed=17, pass_fraction=0.236
- by_asset_class: equity 17/36 (0.472), crypto 0/36 (decisive fail)
- by_vol_regime: low 12/24 (0.500), mid 5/24 (0.208), high 0/24 (0.0)
- best_cell: vol_window=40/h_mult=5.0, QQQ low-vol Sharpe=2.834
- worst_cell: vol_window=40/h_mult=3.0, QQQ high-vol Sharpe=-0.703

Best full-sample config selected: `vol_window=40, h_mult=5.0,
max_hold_days=30` (highest average full-sample Sharpe across QQQ/SPY scan).

## Single-config validator results (best config)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.170 (PASS, thr 1.0) | 18.5% (PASS, thr 25%) | 1.115 (PASS, thr 0.5) | 1.00 (PASS) | 0.125 (PASS) |
| SPY | 0.514 (FAIL, thr 1.0) | 25.5% (FAIL, thr 25%) | 0.444 (FAIL, thr 0.5) | 0.50 (FAIL) | 0.335 (PASS) |

## Decision: ACCEPT (QQQ only)

QQQ passes every validator run at the best config (35 trades over 8.7yr,
Sharpe 1.17, MDD 18.5%, walk-forward 4/4 splits positive). SPY decisively
fails Sharpe/MDD/TC-survival/walk-forward at the same config — the edge does
not transfer to SPY. Crypto (BTC/USDT, ETH/USDT) rejected decisively across
the full grid (0/36 cells). Scope for future loops: this is a QQQ-specific,
low/mid-vol-regime-concentrated trend-event strategy, not a broadly portable
one — do not assume it holds on SPY or crypto without a fresh
symbol-specific retune (same caveat pattern as the already-accepted QP
mean-reversion and Keltner-breakout QQQ-only strategies in this repo).

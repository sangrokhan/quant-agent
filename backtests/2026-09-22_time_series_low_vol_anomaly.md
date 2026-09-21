# 2026-09-22 — Time-Series Low-Volatility Anomaly (Regime-Only Signal)

**Source:** https://www.systemtrader.co/stocks/low-volatility (cross-sectional
low-vol anomaly overview citing Haugen & Baker 1991, Blitz & van Vliet 2007)

**Hypothesis:** Adapt the cross-sectional low-volatility anomaly (low-vol
stocks outperform high-vol stocks on a risk-adjusted basis) to a
single-asset time-series form: stay long QQQ/SPY only while the asset's own
trailing realized volatility is in its low tercile (vs its trailing 252-day
distribution), flat otherwise. No other trigger — the volatility regime
membership IS the entire signal.

## Grid test (Step 6)

`vol_window` in [10, 20, 30] x `low_vol_pct` in [0.25, 0.33, 0.5],
symbols QQQ/SPY (equity) + BTC/USDT, ETH/USDT (crypto), vol_regime_splits=3,
2018-01-01 to 2026-09-01. 108 total cells.

- pass_fraction: 0.204 (22/108)
- by_asset_class: equity 22/54 pass, crypto 0/54 (decisive reject)
- by_vol_regime: low 17/36, mid 1/36, high 4/36 — edge concentrated almost
  entirely in the low-vol tercile itself (expected, since the strategy IS a
  low-vol filter, so "low" tercile cells are near-tautologically favorable)
- best_cell: SPY, vol_window=20/low_vol_pct=0.5, low-vol regime, Sharpe 2.40
- worst_cell: ETH/USDT, vol_window=30/low_vol_pct=0.25, high-vol regime,
  Sharpe -2.09
- Best average equity config across all cells: vol_window=30,
  low_vol_pct=0.33 (mean Sharpe 0.963 across 6 equity cells)

## Single-config validators (Step 7): vol_window=30, low_vol_pct=0.33

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.989 **FAIL** | 0.719 **FAIL** |
| Max drawdown (<=0.25) | 0.134 PASS | 0.139 PASS |
| TC survival (net Sharpe >=0.5, 10bps, 52/64 trades) | 0.902 PASS | 0.581 PASS |
| Walk-forward (4-split, >=0.75 pass) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (relative_std <=0.5) | 0.894 **FAIL** | 0.376 PASS |

## Decision: REJECTED

QQQ and SPY both fail the primary Sharpe threshold (0.989 and 0.719 vs 1.0),
and QQQ additionally fails parameter sensitivity (relative_std 0.894 —
Sharpe swings widely across the vol_window/low_vol_pct grid, from ~0.3 to
~1.5+). Max drawdown, TC-survival, and walk-forward all pass cleanly,
suggesting the underlying regime-timing idea has some structure (it does cut
drawdown materially: 13-14% vs a raw buy-and-hold QQQ/SPY MDD that's
typically 25%+), but doesn't clear the Sharpe bar to be accepted outright.
Crypto is decisively rejected (0/54 grid cells) — realized-vol-tercile
timing does not help on BTC/ETH, likely because "low realized vol" regimes
in crypto still carry enough tail risk / regime persistence issues that the
filter doesn't add edge the way it modestly does on equity indices.

**Note for future loops:** this near-miss could be revisited by pairing the
vol-regime filter with a trend/momentum overlay (rather than trading the
regime alone) — e.g. long only when BOTH low-vol regime AND price above its
own trend SMA, which might rescue the Sharpe shortfall while keeping the
drawdown benefit. Also worth trying a wider trailing lookback (vol_lookback)
or asymmetric entry/exit thresholds (enter <0.25 quantile, exit >0.5
quantile) to reduce whipsaw switching (52-64 trades already fairly high for
a "regime" filter).

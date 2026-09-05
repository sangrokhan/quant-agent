# SPY/TLT Stock-vs-Bond Ratio SMA-Crossover Regime Filter — Backtest Report

**Hypothesis:** SPY/TLT ratio fast-SMA vs slow-SMA crossover signals a
stock-vs-bond risk regime: fast > slow (stocks leading bonds) -> long;
fast < slow (bonds leading, flight-to-safety) -> flat.

**Source:** https://aveceasar.github.io/ratios/spy-tlt/ (ChartVault
charting tool) -- "A rising line means SPY is outperforming TLT... the
most important reversals are the ones that break a long trend." No
specific backtest/threshold given by the source itself; this backtest
operationalizes the charting methodology's own suggested SMA-crossover
framing (site displays SMA20/50/200 overlays).

**Strategy file:** `strategies/2026-09-05_spy_tlt_ratio_regime.py`

## Step 6 — Grid test summary (param_grid: fast_window in [10,20,30] x
slow_window in [50,100,150]; symbols: equity QQQ/SPY, crypto BTC/USDT,
ETH/USDT; vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 108, passed_cells: 24, **pass_fraction: 0.222**
- by_asset_class: equity 24/54 (44%), crypto 0/54 (0%).
- by_vol_regime: low 18/36, mid 6/36, high 0/36.
- best_cell: fast_window=10, slow_window=100, QQQ, low-vol regime,
  Sharpe=2.56 (tercile slice, not full period).

## Step 7 — Single-config validators (best grid config over FULL period:
fast_window=10, slow_window=100)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.776 | FAIL 0.743 |
| Max Drawdown (<= 0.25) | FAIL 0.424 | FAIL 0.321 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 31 trades) | PASS 0.747 | PASS 0.703 |
| Parameter sensitivity (relative_std <= 0.5, 9-cell QQQ sweep) | PASS 0.185 | n/a |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version, consistent with other entries).

## Outcome: **REJECTED**

Full-period Sharpe and MDD fail decisively on both QQQ and SPY at the best
grid config; the grid's headline Sharpe=2.56 was, as with several other
strategies tested this session, a single low-vol-tercile artifact rather
than a full-period effect. A slow-moving fast/slow SMA crossover on the
SPY/TLT ratio is too lagging to time the QQQ/SPY drawdowns it needs to
avoid to control MDD (0.42/0.32 both decisively over the 0.25 threshold).
Crypto again fails completely (0/54). Consistent with the emerging pattern
this session: cross-asset relative-value ratios only clear full validation
when the underlying assets have low mutual correlation and independent
information content (gold/silver, 2026-09-05-030, accepted) -- SPY vs its
own long-bond hedge (TLT) apparently doesn't carry enough independent
signal at this SMA-crossover implementation to beat full-period buy-and-
hold risk-adjusted.

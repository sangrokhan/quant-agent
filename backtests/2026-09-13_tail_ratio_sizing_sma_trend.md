# Tail-Ratio Dynamic Sizing on SMA(200) Trend Gate

**Hypothesis:** Per https://www.pfolio.io/academy/tail-ratio (read via
browser_exec; tradesviz.com's equivalent page hit a Cloudflare 502 and was
unhelpful): Tail Ratio = |R(95th percentile)| / |R(5th percentile)| of a
return distribution. Percentile-based (robust to a single extreme outlier,
unlike skewness), structurally distinct from every drawdown/mean-based
sizing overlay tested this cron trigger (Omega, GPR, Pain, Burke, Sterling,
MAR/Calmar, downside-deviation, CVaR) and from the OLS-regression-based
K-Ratio (also tested this trigger, rejected). Per the source, trend-
following strategies structurally show tail ratios >1 (long right tail from
riding trends, tight left tail from stop-outs); this strategy scales an
SMA(200) trend gate's exposure by the trailing tail ratio of the underlying
asset itself. First Tail-Ratio-based sizing strategy in this repo.

**Sources:** https://www.pfolio.io/academy/tail-ratio (tradesviz.com
attempted but Cloudflare 502-blocked)

## Grid test summary (equity: QQQ/SPY, crypto: BTC/USDT/ETH/USDT;
tail_window in [60,90,120], tail_ratio_reference in [0.8,1.0,1.3];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, tail_window=60, tail_ratio_reference=0.8, low-vol, Sharpe=2.84
- worst_cell: ETH/USDT, tail_window=90, tail_ratio_reference=0.8, mid-vol, Sharpe=0.04

Crypto never fails as decisively negative as most prior overlays (worst cell
is a near-zero Sharpe, not sharply negative), but 0/54 grid cells still pass
the 1.0 min-Sharpe bar -- same structural non-transfer pattern as every
prior SMA(200)-gated sizing overlay this cron trigger.

## Single-config validator results (best full-sample config: tail_window=60,
tail_ratio_reference=0.8, trend_window=200, leverage_cap=1.0)

### SPY -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.052 | >= 1.0 | Yes |
| Max drawdown | 0.208 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 151 trades) | 0.914 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 6-combo grid) | 0.029 | <= 0.5 | Yes |

### QQQ -- ACCEPTED (4/4 run)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.299 | >= 1.0 | Yes |
| Max drawdown | 0.212 | <= 0.25 | Yes |
| Net Sharpe after costs (5bps/trade, 102 trades) | 1.237 | >= 0.5 | Yes |
| Parameter sensitivity (relative std across 6-combo grid) | 0.029 | <= 0.5 | Yes |

`validators.check_walk_forward` was skipped -- `vbt.utils.splitting.RangeSplitter`
is not available in the installed vectorbt version (pre-existing tooling gap
noted since 2026-09-13-007; not specific to this strategy).

## Decision

**Accepted for both SPY and QQQ** (equity only). All four validators run
pass comfortably for both symbols at the shared config tail_window=60,
tail_ratio_reference=0.8. Parameter sensitivity is very low (2.9% relative
std across the 6-combo grid), and the effect is directionally consistent:
better Sharpe in low-vol regimes, weaker in mid, failing in high-vol --
matching the broader pattern already established for this repo's SMA(200)-
gate sizing-overlay family. Crypto (BTC/USDT, ETH/USDT) rejected across the
whole grid (0/54 cells), consistent with every prior sizing-overlay tested
this cron trigger; no crypto-specific tail-ratio structure survives on top
of the SMA(200) gate.

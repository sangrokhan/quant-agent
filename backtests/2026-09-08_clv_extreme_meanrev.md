# CLV Extreme Mean Reversion — Backtest Report (2026-09-08)

## Hypothesis
Close Location Value (CLV) = ((Close-Low)-(High-Close))/(High-Low), a
single-bar (non-cumulative) measure of where within the bar's range the
close occurred. A sharp single-bar close-at-the-low (CLV <= -0.6, an
extreme one-bar selling climax) occurring while price is in an established
uptrend (close > SMA(100)) signals a fadeable overextension; long entry on
that bar, exit when CLV recovers >= 0.2 (buying pressure returning), trend
filter breaks, or an 8-day time-stop.

Distinct from this repo's existing cumulative Accumulation/Distribution
line strategy (2026-09-04-047, a running-total trend-confirmation tool)
and from the IBS family (different normalization, ignores the high-side
symmetric term).

Sources: https://www.investopedia.com/terms/c/close_location_value.asp ;
https://www.vtmarkets.com/en-eu/discover/accumulation-distribution/

## Grid test summary (extreme_threshold=[-0.5,-0.6,-0.7] x
recovery_threshold=[0.0,0.2] x max_hold_days=[5,8], QQQ/SPY/BTC-USDT/
ETH-USDT, vol_regime_splits=3, 2018-2026)

- total_cells=144, passed=32, pass_fraction=0.222
- by_asset_class: equity 32/72, crypto 0/72 (decisive crypto rejection)
- by_vol_regime: low 14/48, mid 10/48, high 8/48 (edge present across all
  three regimes, tilted toward low-vol)
- best_cell: SPY low-vol, extreme_threshold=-0.6/recovery_threshold=0.2/
  max_hold_days=8, Sharpe 2.20
- worst_cell: SPY mid-vol, Sharpe -0.06 (near flat, not a large loss)

## Single-config validators (extreme_threshold=-0.6, recovery_threshold=0.2,
max_hold_days=8)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full-sample) | 1.023 PASS | 1.002 PASS | >= 1.0 |
| Max drawdown | 0.174 PASS | 0.117 PASS | <= 0.25 |
| TC survival (5bps/trade, net Sharpe) | 0.788 PASS (196 trades) | 0.689 PASS (201 trades) | >= 0.5 |
| Walk-forward (4-split manual contiguous; vectorbt RangeSplitter API mismatch, documented workaround) | 3/4 PASS (0.75) | 3/4 PASS (0.75) | >= 0.75 |
| Parameter sensitivity (relative std, 4-point nearby-param sweep) | 0.051 PASS | 0.104 PASS | <= 0.5 |

Crypto (BTC/USDT, ETH/USDT): rejected decisively, 0/72 grid cells passed.

## Decision: ACCEPT (QQQ AND SPY, broad equity scope)

Both symbols pass all five validators, though both Sharpe passes are
razor-thin (1.023/1.002) and both walk-forward splits pass at exactly the
0.75 threshold (3 of 4 contiguous splits positive). Crypto is decisively
out of scope (0/72 grid cells).

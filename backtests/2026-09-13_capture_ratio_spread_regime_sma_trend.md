# Up/Down Capture Ratio Spread Regime Filter on SMA(200) Trend Gate

**Hypothesis:** Per https://metricgate.com/docs/up-down-capture-ratio/
(browser_exec): Up-Capture (UC) = 100 * R_p^up / R_b^up, Down-Capture (DC)
= 100 * R_p^down / R_b^down (geometric compounded returns split by
benchmark sign vs SPY); capture spread = UC - DC. Fundamentally different
construction from every ratio-based sizing overlay already tested in this
repo (all single-number ratios over the whole trailing window) -- capture
ratios split the window by benchmark sign and compare compounded
participation separately for up/down periods. Used as a binary regime
filter (trade only when capture_spread > spread_threshold) layered on the
SMA(200) trend gate. First Up/Down-Capture-Ratio-based strategy in this
repo.

**Source:** https://metricgate.com/docs/up-down-capture-ratio/

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
capture_window in [60,90,120], spread_threshold in [-10.0,0.0,10.0];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 24, pass_fraction: 0.222
- by_asset_class: equity 24/54 passed, crypto 0/54 passed
- by_vol_regime: low 13/36, mid 9/36, high 2/36
- best_cell: QQQ, capture_window=60, spread_threshold=-10.0, low-vol, Sharpe=3.006
- worst_cell: QQQ, capture_window=60, spread_threshold=10.0, high-vol, Sharpe=-0.665

## Single-config validator results (best full-sample config per symbol:
capture_window=60, spread_threshold=0.0, trend_window=200, leverage_cap=1.0)

| Symbol | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed | Num trades |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 1.123 | Yes | 0.058 | Yes | 0.393 | No (thr 0.5) | 1.00 | Yes | 0.923 | No (thr 0.5) | 290 |
| QQQ | 1.311 | Yes | 0.219 | Yes | 1.256 | Yes | 0.75 | Yes | 0.224 | Yes | 88 |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold).

SPY generates a much higher trade count (290 vs QQQ's 88) at this config --
the capture-spread regime flips frequently for SPY around the zero
threshold, so transaction costs erode the otherwise-strong gross Sharpe,
and the parameter sweep's Sharpe values swing widely (relative std 0.92)
as `spread_threshold`/`capture_window` shift the flip frequency.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ (capture_window=60,
spread_threshold=0.0). SPY fails transaction-cost survival (net Sharpe
0.393 < 0.5 threshold after 5bps/trade drag from 290 trades) and parameter
sensitivity (relative std 0.923, more than the 0.5 threshold) -- a
decisive, not near-miss, rejection driven by excessive turnover. Crypto
(BTC/USDT, ETH/USDT) rejected decisively across the whole grid (0/54
cells).

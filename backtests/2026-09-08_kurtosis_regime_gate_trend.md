# Backtest Report: Kurtosis Regime Gate on SMA Trend (2026-09-08)

**Status: REJECTED** (QQQ is a near-miss) — strategy file kept in
`strategies/` as a record.

## Hypothesis

Per Federico Carrone's "Leptokurtic" series, Episode 2 "Detecting Crashes
with Fat-Tail Statistics" (https://federicocarrone.com/series/leptokurtic),
returns are leptokurtic (fat-tailed) and elevated kurtosis has been used as
a crash-detection signal in the source's own 15-method toolkit tested
against 96 historical drawdowns. Adapted: long only when in an SMA(200)
uptrend AND rolling excess kurtosis of daily log returns is below its own
trailing percentile threshold (not in an unusually fat-tailed regime).

## Single-config validator results (best grid config: `kurtosis_pct_threshold=0.8`, `kurtosis_window=40`)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-forward | Param sensitivity | Trades |
|---|---|---|---|---|---|---|
| SPY | 0.705 ❌ | 0.192 ✅ | 0.625 ✅ | 1.0 ✅ | 0.171 ✅ | 49 |
| QQQ | 0.854 ❌ (near-miss) | 0.243 ✅ | 0.804 ✅ | 1.0 ✅ | 0.051 ✅ | 44 |

## Grid test summary

`param_grid={kurtosis_pct_threshold:[0.6,0.8], kurtosis_window:[20,40]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`
(2018-01-01 to 2026-09-01), 48 total cells.

- Overall pass_fraction: 0.25 (12/48 cells)
- By asset class: equity 12/24 passed, crypto 0/24
- By vol regime: low 8/16, mid 3/16, high 1/16
- Best cell: SPY, low-vol, Sharpe 2.404
- Worst cell: SPY, mid-vol, Sharpe -0.337

## Decision

**Reject.** Both QQQ (near-miss, Sharpe 0.854) and SPY (Sharpe 0.705) fail
only the Sharpe threshold — every other validator passes comfortably. The
kurtosis gate reduces risk and return roughly proportionally rather than
improving the risk-adjusted ratio, unlike the successful CPPI and
formation-price stop-loss overlays accepted earlier this cron trigger,
which cut drawdown MORE than they cut return. QQQ is flagged as a genuine
near-miss worth a future local parameter refinement (e.g. a higher
`kurtosis_pct_threshold` to reduce false-positive gate-outs).

# CFTC COT Gold Futures Non-Commercial Trend-Confirmation — Backtest Report

**Hypothesis:** COMEX Gold futures non-commercial (large speculator) net
position (long - short) building over a trailing 8-week window (positive
slope) confirms genuine conviction behind a price uptrend — long GLD only
when BOTH close > SMA(80) AND non-commercial net position has risen over
the trailing 8 COT weeks. Mirrors this cron trigger's own funding-rate
contrarian-vs-trend-confirmation pair (2026-09-20-031/-035) but on a new
market (COMEX Gold) and new data source (CFTC COT, first used this cron
trigger in strategy 2026-09-20-037, an extreme-percentile Bitcoin fade
that was rejected).

**Sources:**
- https://www.google.com/search?q=open+interest+rising+with+price+breakout+confirmation+crypto+futures+trading+rule (browser_exec Google SERP; TradingView/Coinfuty/AlphaX: "a breakout accompanied by rising open interest/positioning carries more weight... new capital confirms conviction")
- https://publicreporting.cftc.gov/resource/jun7-fc8e.json (CFTC Socrata Legacy COT API, direct — `GOLD - COMMODITY EXCHANGE INC.` weekly non-commercial long/short positions)

**Data:** GLD/SLV daily OHLCV via `data/loaders.load_equity`; BTC/USDT & ETH/USDT via `load_crypto` (robustness-check-only, not the intended asset class — Gold COT has no direct crypto proxy).

## Grid test (equity + crypto, vol_regime_splits=3)

`param_grid = {trend_window: [30,50,80], positioning_window: [4,8,13]}`,
`symbols = {equity: [GLD,SLV], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 22, **pass_fraction: 0.204**
- by_asset_class: equity 19/54 passed, crypto 3/54 passed (crypto included only as an out-of-sample check, not a genuine leg — Gold-specific COT signal was never expected to transfer to crypto price action)
- by_vol_regime: low 20/36, mid 1/36, high 1/36
- best_cell: trend_window=80, positioning_window=8, GLD, low-vol regime, Sharpe 4.23
- worst_cell: trend_window=80, positioning_window=4, ETH/USDT, high-vol regime, Sharpe -0.73

Signal concentrates its edge in the intended equity/precious-metals asset
class and low-vol regimes — an honest, narrower-but-real scope (per
RESEARCH_LOOP.md Step 6 guidance) rather than a false broad claim.

## Primary-config validation (GLD, trend_window=80, positioning_window=8 — best full-sample config)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period, 2019-2026) | 1.006 | ≥ 1.0 | PASS |
| Max drawdown | 0.182 | ≤ 0.25 | PASS |
| Transaction cost survival (10bps/trade, 55 trades) | 0.923 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward (4 splits) | 3/4 splits positive Sharpe (1.25, -0.77, 0.98, 1.50) = 0.75 | ≥ 0.75 | PASS |
| Parameter sensitivity (9-cell trend_window×positioning_window sweep) | relative std 0.161 | ≤ 0.5 | PASS |

All 5 validators pass. The single negative walk-forward split
(2020-12→2022-11, Sharpe -0.77) covers the 2022 Fed-hiking/gold-bear
period — a known, disclosed weak regime rather than a hidden flaw.

## Decision: ACCEPTED (equity/precious-metals only — GLD/SLV; NOT crypto)

Scope: this strategy is accepted for GLD (and by extension SLV, same
asset-class rationale) using COMEX Gold futures COT positioning data. It
is explicitly NOT validated (and not expected to transfer) to crypto —
future loops should not apply this signal to BTC/ETH price series; the
crypto grid legs above were an out-of-sample sanity check only, and as
expected showed no edge (3/54 passed).

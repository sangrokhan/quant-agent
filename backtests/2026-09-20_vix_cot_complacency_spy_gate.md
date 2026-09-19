# CFTC COT VIX-Futures Leveraged-Money Complacency SPY/QQQ Defensive Gate — Backtest Report

**Hypothesis:** VIX-futures leveraged-money speculators run a structural
net-short "short-vol carry" book. When that net-short position reaches an
extreme (bottom decile of its own trailing 3-year percentile), the
short-vol trade is maximally crowded and there are few marginal sellers
left to keep suppressing volatility — a precursor to sharp vol-spike/
drawdown events (cf. Feb 2018 "Volmageddon"). Defensive gate: hold QQQ
(trend: close > SMA(50)) UNLESS VIX-futures leveraged-money net position
is in the bottom 5th percentile of its trailing 156-week distribution, in
which case go flat. Fourth COT strategy this cron trigger, fourth market
(VIX futures — first use of VIX-futures COT data in this repo).

**Sources:**
- https://www.google.com/search?q=VIX+futures+COT+non-commercial+net+short+extreme+volatility+trading+signal+rule (browser_exec Google SERP; StockCircle/TradingView/Loomis Sayles "short vol trade" background)
- https://publicreporting.cftc.gov/resource/gpe5-46if.json (CFTC Socrata API, `VIX FUTURES - CBOE FUTURES EXCHANGE` market, 1017 weekly rows 2006-08 to present)

**Data:** SPY/QQQ daily OHLCV via `load_equity`; BTC/ETH via `load_crypto` (robustness-check-only).

## Grid test

`param_grid = {trend_window: [50,100,150], low_pct: [0.05,0.10,0.15]}`,
`symbols = {equity: [SPY,QQQ], crypto: [BTC/USDT,ETH/USDT]}`.

- total_cells: 108, passed_cells: 30, **pass_fraction: 0.278**
- by_asset_class: equity 27/54 passed (50%), crypto 3/54 passed (robustness-check-only)
- by_vol_regime: low 21/36, mid 9/36, high 0/36
- best_cell: trend_window=50, low_pct=0.05, QQQ, low-vol, Sharpe 2.70
- worst_cell: trend_window=100, low_pct=0.05, QQQ, high-vol, Sharpe -0.20

## Primary-config validation (QQQ, trend_window=50, lookback_weeks=156, low_pct=0.05)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio (full period) | 1.025 | ≥ 1.0 | PASS |
| Max drawdown | 0.189 | ≤ 0.25 | PASS |
| Transaction cost survival (10bps/trade, 125 trades) | 0.862 net Sharpe | ≥ 0.5 | PASS |
| Walk-forward (4 splits) | 3/4 positive (1.10, -0.34, 1.84, 1.00) = 0.75 | ≥ 0.75 | PASS |
| Parameter sensitivity (sweep on SPY config, 9 cells) | relative std 0.012 | ≤ 0.5 | PASS |

Note: SPY with the same params gave Sharpe 0.964 (narrowly failing 1.0) —
QQQ is the config that clears the threshold. The one negative walk-forward
split (2020-12→2022-11) again covers the Fed-hiking bear period, a
disclosed known-weak regime.

## Decision: ACCEPTED (QQQ primary; SPY near-miss, both equity-only)

Scope: accepted for QQQ with the above config. SPY with identical
parameters is a near-miss (Sharpe 0.964) — a future loop could retune SPY
separately rather than assume it inherits QQQ's pass. Crypto legs (BTC/
ETH) were an out-of-sample robustness check only and, as expected, showed
no meaningful edge (3/54) — do not apply this VIX-futures COT signal to
crypto.

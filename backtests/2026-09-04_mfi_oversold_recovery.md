# MFI Oversold-Recovery Mean Reversion — Backtest Report

**Hypothesis** (kb id 2026-09-04-033): MFI(14) dropping to/below an
oversold threshold (20-25) and then crossing back above it signals a
short-term mean-reversion buy, gated by close > 200d SMA (uptrend-drift
proxy). Long-only, exit on MFI >= 80 or after max_hold_days.

**Source**: Google AI-overview + quantifiedstrategies.com MFI article
(fetched via browser_exec after web_search failed with a DDGS/Yahoo TLS
connection error this iteration). Source's own concrete rule additionally
requires an engulfing-candlestick confirmation and a range-bound market
classification, neither implementable with this repo's OHLCV-only daily
loaders — this strategy tests the closest testable core mechanism (pure
MFI threshold-recovery cross + trend filter) as a simplification.

## Grid test (Step 6)

`param_grid = {mfi_window: [10,14], oversold_threshold: [20,25], max_hold_days: [8,12]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 96 total cells.

- pass_fraction: **0.083** (8/96)
- by_asset_class: equity 8/48, crypto 0/48
- by_vol_regime: low 0/32, mid 2/32, high 6/32
- best_cell: SPY, mfi_window=14, oversold_threshold=25, max_hold_days=12, high-vol tercile, Sharpe 1.739 (not representative of full sample, see below)

## Full-sample validators (Step 7) — grid-best config (mfi_window=14, oversold_threshold=25, max_hold_days=12)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.019 (fail, thr 1.0) | 0.224 (pass, thr 0.25) | 0.005 (fail, thr 0.5) | 8 |
| SPY | 0.932 (fail, thr 1.0, near-miss) | 0.038 (pass) | 0.900 (pass) | 6 |

Parameter sensitivity (mfi_window in {10,14,20} on SPY, oversold=25, hold=12):
relative std 1.914 vs 0.5 ceiling — **fails decisively**. Sharpe swings widely
across nearby window choices, consistent with the very low trade counts
(6-8 trades over 7.7 years) making the full-sample metric noisy/unstable.

## Decision: REJECTED (all asset classes)

QQQ fails Sharpe and net-Sharpe decisively. SPY is a near-miss on Sharpe
alone (0.932 vs 1.0), but parameter sensitivity fails badly (rel.std 1.91),
indicating the near-miss result is not a robust property of the strategy —
it is highly sensitive to the exact MFI lookback window, likely because so
few trades (6) occur over the full sample that a couple of trade
inclusions/exclusions swing the Sharpe substantially. Crypto rejected
decisively at grid stage (0/48 cells). Walk-forward skipped (Sharpe/param-
sensitivity already give a clear reject signal, per Step 7 minimum-subset
guidance).

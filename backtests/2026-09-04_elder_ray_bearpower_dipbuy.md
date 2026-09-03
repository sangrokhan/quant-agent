# Elder-Ray Bear-Power-Rising Dip-Buy — Backtest Report

**Hypothesis** (kb id 2026-09-04-037): a 13-period EMA "consensus of value"
baseline; long entry when EMA is rising AND Bear Power (low - EMA) is
negative but rising from a lower level (sellers losing dominance during a
pullback within an uptrend); exit on Bull Power (high - EMA) making a
lower high or Bear Power dropping sharply again.

**Source**: Google AI-overview + TradingView/QuantifiedStrategies snippets
(web_search failed with a DDGS/Yahoo TLS connection error this iteration,
fell back to browser_exec). Long-only implementation per this repo's
convention (source's symmetric short-side rule not implemented).

## Grid test (Step 6)

`param_grid = {ema_window: [13,21], bear_power_exit_drop: [0.01,0.02]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3,
2019-01-01 to 2026-09-01. 48 total cells.

- pass_fraction: **0.104** (5/48)
- by_asset_class: equity 5/24, crypto 0/24
- by_vol_regime: low 4/16, mid 1/16, high 0/16
- best_cell: QQQ, ema_window=13, bear_power_exit_drop=0.01, low-vol tercile, Sharpe 1.309 (not representative of full sample, see below)

## Full-sample validators (Step 7) — grid-best config (ema_window=13, bear_power_exit_drop=0.01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.155 (fail, thr 1.0) | 0.158 (pass, thr 0.25) | 0.011 (fail, thr 0.5) | 57 |
| SPY | 0.200 (fail, thr 1.0) | 0.115 (pass) | 0.026 (fail) | 50 |

## Decision: REJECTED (all asset classes)

Full-sample Sharpe on both QQQ (0.155) and SPY (0.200) is close to zero,
far below the 1.0 threshold -- the grid's apparent best cell (low-vol
tercile Sharpe 1.31) was not representative. Net-of-cost Sharpe collapses
further (0.011-0.026) with a high trade count (50-57 over 7.7 years) for a
mean-reversion/pullback strategy, indicating the entry condition (Bear
Power rising from a lower negative level) fires too often on ordinary noisy
pullbacks that don't resolve favorably. Walk-forward and parameter
sensitivity skipped per Step 7 minimum-subset guidance (Sharpe already
fails decisively on both tested symbols). Crypto rejected decisively (0/24
grid cells).

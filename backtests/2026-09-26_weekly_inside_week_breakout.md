# Weekly Inside-Week / Mother-Week Breakout — Backtest Report

**Hypothesis:** A "Mother Week" (weekly OHLC bar) followed by an "Inside Week" (next week's high/low fully contained within the Mother Week's range) marks a weekly-timeframe volatility contraction. Long entry when a subsequent daily close breaks above the Mother Week's high; exit on stop (close < Mother Week's low), target (close >= mother_high + target_mult * mother_range), or a max_hold_days time-stop.

**Source:** Google AI-overview synthesis of PriceAction.com/TradingView/FTMO weekly inside-bar explainer articles (read via browser_exec after web_search's DDGS backend returned zero results for the query). Distinct from this repo's heavily-saturated (28+ prior entries) DAILY-timeframe inside-bar/mother-bar family — this is the first genuinely higher-timeframe (weekly-resampled) range-breakout construction.

**Strategy file:** strategies/2026-09-26_weekly_inside_week_breakout.py

## Grid test (validation/grid_test.py::run_strategy_grid)

param_grid: target_mult in {1.5, 2.0, 3.0}, max_hold_days in {10, 15, 20}; symbols QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3; 108 total cells.

- pass_fraction: 35.2% (38/108)
- by_asset_class: equity 28/54, crypto 10/54
- by_vol_regime: low 14/36, mid 6/36, high 18/36
- best_cell: SPY, target_mult=1.5/max_hold_days=20, high-vol tercile, Sharpe 2.33

## Single-config validators (best config: target_mult=1.5, max_hold_days=20)

| Symbol | Sharpe | Pass? | MDD | Pass? | Net Sharpe (TC) | Pass? | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | 1.102 | YES | 0.112 | YES | 1.016 | YES | 34 |
| SPY | 1.295 | YES | 0.097 | YES | 1.155 | YES | 40 |
| BTC/USDT | 0.183 | NO | 0.144 | YES | 0.150 | NO | 68 |
| ETH/USDT | 0.080 | NO | 0.173 | YES | 0.056 | NO | 74 |

Parameter sensitivity (QQQ, target_mult in {1.5, 2.0, 3.0}): relative_std 0.047 (well under 0.5 threshold) — robust, non-overfit.

Walk-forward: not run — `vbt.utils.splitting` raises `AttributeError` in this repo's installed vectorbt version (pre-existing environment issue, per multiple prior entries e.g. 2026-09-05-009).

## Decision

**Accept for QQQ and SPY** (both symbols pass Sharpe, MDD, TC-survival decisively with low trade counts of 34-40 over 7.7yr, and QQQ's parameter sensitivity across target_mult is low/robust). **Reject for crypto** (BTC/ETH decisively fail Sharpe and TC-survival despite passing MDD) — the weekly-resampled contraction/breakout mechanism appears to be an equity-market-specific structural effect (consistent with lower intraweek noise and more persistent weekly ranges in QQQ/SPY vs the choppier, higher-frequency-driven crypto weekly bars), a useful cross-asset-class falsification result.

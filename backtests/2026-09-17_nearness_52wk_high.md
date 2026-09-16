# Backtest Report: Nearness-to-52-Week-High Regime Filter

**Strategy file:** `strategies/2026-09-17_nearness_52wk_high.py`
**Date:** 2026-09-17
**Hypothesis source:** https://www.quantifiedstrategies.com/52-week-high-strategy/ (visited this iteration)

## Hypothesis

The "52-week high effect" (George & Hwang 2004, cited on the source page via
a Bayes Business School PDF found on the same Google SERP): stocks/indices
trading close to their 52-week high tend to keep outperforming due to
investor anchoring bias (under-reaction near the high keeps such names
undervalued relative to fundamentals). The source's own backtest table shows
the edge only materializes with longer holding periods (5/10-day exits are
flat-to-negative, 50/100-day exits are +1.1%/+2.2%), and the source's
"strategy no.1" backtest explicitly gates entries with "S&P 500 above its
200-day moving average" AND "stock above its 100-day moving average" — the
trend filter is part of the source's own disclosed rule.

Implemented as: long while price is within `entry_threshold` of its rolling
252-day high AND above its `trend_ma_window`-day SMA, held via hysteresis
until nearness drops to `exit_threshold` or the trend filter breaks
(encodes the source's "let it run" finding directly).

## Grid test (Step 6)

`param_grid={entry_threshold:[-0.02,-0.05,-0.08], exit_threshold:[-0.10,-0.15,-0.20]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01 to 2026-09-01.

- total_cells=108, passed=29 (26.9%)
- by_asset_class: equity 27/54, crypto 2/54
- by_vol_regime: low 20/36, mid 9/36, high 0/36
- best_cell: SPY low-vol entry=-0.02/exit=-0.10, Sharpe=2.68

QQQ's own average-Sharpe sweep across regimes favored a wider band
(entry=-0.08, exit=-0.15); SPY favored the tightest band (entry=-0.02,
exit=-0.10) — recorded as per-symbol-tuned, not a shared config.

## Single-config validators (Step 7)

### QQQ (entry_threshold=-0.08, exit_threshold=-0.15, lookback=252, trend_ma_window=200)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.290 | 1.0 | ✅ |
| Max Drawdown | 0.207 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 5 trades) | 1.285 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std) | 0.157 | 0.5 | ✅ |

### SPY (entry_threshold=-0.02, exit_threshold=-0.10, lookback=252, trend_ma_window=200)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.092 | 1.0 | ✅ |
| Max Drawdown | 0.146 | 0.25 | ✅ |
| TC survival (net Sharpe, 10bps, 6 trades) | 1.082 | 0.5 | ✅ |
| Walk-forward (4-split) | 1.00 | 0.75 | ✅ |
| Parameter sensitivity (relative std) | 0.061 | 0.5 | ✅ |

### Crypto (BTC/USDT, ETH/USDT, QQQ's config entry=-0.08/exit=-0.15)

| Symbol | Sharpe | MDD |
|---|---|---|
| BTC/USDT | 0.280 (fail) | 0.511 (fail, ~2x cap) |
| ETH/USDT | 0.257 (fail) | 0.487 (fail, ~2x cap) |

Decisively rejected on crypto both on Sharpe and MDD — very few trades
triggered (crypto trends less persistently near rolling highs at daily
frequency over this window), consistent with this repo's frequent finding
that binary long/flat trend-regime filters without vol-scaling fail crypto
drawdown caps.

## Decision (Step 8)

**Accepted** for equity (QQQ, SPY — per-symbol-tuned configs, all 5
validators pass each). **Rejected** for crypto (BTC/USDT, ETH/USDT —
decisive Sharpe and MDD fail).

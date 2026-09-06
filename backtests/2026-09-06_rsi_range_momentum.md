# Backtest Report: RSI Range-Momentum (Arthur Hill)

**Strategy file:** `strategies/2026-09-06_rsi_range_momentum.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-184

## Hypothesis

RSI used as a MOMENTUM confirmation indicator (not the usual mean-reversion
oscillator use tested extensively elsewhere in this repo): per Arthur
Hill's "Finding consistent trends with strong momentum" (as summarized by
QuantifiedStrategies.com), an uptrend is confirmed when, over a rolling
lookback window, (a) RSI never dropped below 40 ("RSI Bull Range") AND (b)
RSI's max value exceeded 70 at some point ("RSI Bull Momentum"). Long entry
when both true; exit only when BOTH flip false simultaneously (asymmetric
persistence -- staying in if only one condition breaks). Source's own SPY
backtest (1993-present): CAGR 5.93% (vs buy-hold 9.58%), 35.7% time in
market, 12 trades, 83% win rate, MDD 12.9%.

**Source:** `https://www.quantifiedstrategies.com/rsi-range-momentum-trading-strategy/`
(reached via `browser_exec` Google search fallback after `web_search`
returned zero results for the sector-rotation query that led here). First
RSI-as-momentum strategy in this repo.

## Step 6 grid summary

Param grid: `lookback_window in {60, 100, 150}` x
`bull_momentum_threshold in {65.0, 70.0}` (fixed `rsi_window=14,
bull_range_low=40.0`), symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT,
ETH/USDT]}`, `vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.125** (9/72)
- **by_asset_class:** equity 9/36; **crypto 0/36** (decisive fail)
- **by_vol_regime:** low 8/24, mid 0/24, high 1/24 -- strongly concentrated
  in low-vol regime
- **best_cell:** `lookback_window=100, bull_momentum_threshold=65.0`,
  SPY/low-vol, Sharpe 1.95
- **worst_cell:** `lookback_window=150, bull_momentum_threshold=65.0`,
  SPY/mid-vol, Sharpe -0.88

## Step 7 single-config validators (best config: SPY, `lookback_window=100,
bull_momentum_threshold=65.0`, full sample 2018-2026-09)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | 0.723 | ≥ 1.0 |
| max_drawdown | ✅ | 0.190 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, **3 trades total**) | ✅ | net Sharpe 0.719 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback) | ✅ | 4/4 splits positive | ≥ 0.75 |
| parameter_sensitivity (6-cell grid) | ❌ | relative std 1.168 | ≤ 0.5 |

## Decision: **REJECT**

Full-sample Sharpe (0.723) misses the 1.0 threshold, and unlike the KAMA
near-miss earlier this trigger, this rejection is reinforced by a decisive
parameter-sensitivity failure (relative std 1.168, more than double the 0.5
threshold) -- performance swings wildly across the 6-cell lookback/threshold
grid, consistent with the strategy generating extremely few trades (only 3
over ~8.7 years at the best config) so headline metrics are dominated by
idiosyncratic single-trade outcomes rather than a repeatable edge. This
matches the source's own observation that the strategy "does not generate a
ton of signals" -- at daily-bar/single-symbol scale, the low trade count
makes this an unreliable backtest regardless of the favorable win rate the
source reported (which was itself based on only 12 trades over 30 years).
Not flagged for revisiting with a parameter tweak, since the core issue
(insufficient trade frequency for statistical reliability at this
lookback/threshold combination) is structural to the strategy design, not a
fixable threshold-tuning problem.

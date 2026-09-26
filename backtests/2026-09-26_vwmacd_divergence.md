# Backtest Report: Volume-Weighted MACD (VW-MACD) Divergence

**Strategy file:** `strategies/2026-09-26_vwmacd_divergence.py`
**KB id:** 2026-09-26-065
**Outcome:** REJECTED

## Hypothesis

Source: Google AI-overview synthesis (browser_exec Google SERP fallback;
web_search DDGS backend returned "No results found" for this query),
citing LuxAlgo, Evest, "Quant Tactics", "CodeTrading" consistently: a
Volume-Weighted MACD (VW-MACD) DIVERGENCE strategy. Bullish divergence =
price makes a lower swing low while the VW-MACD line makes a higher swing
low (selling pressure lacks volume conviction); trigger on VW-MACD crossing
back above its signal line. Bearish divergence (exit condition here, no
short leg, long-only) = price higher high + VW-MACD lower high, trigger on
crossing below signal.

Distinct from every prior VW-MACD entry in this KB (2026-09-04-142,
2026-09-06-113, 2026-09-18-061, 2026-09-18-062: bare signal-line crossovers;
2026-09-14-155/2026-09-15-004: histogram continuous-sizing dial) — this is
the first requiring a genuine price-vs-indicator swing-structure
disagreement as an entry precondition.

## Grid summary (Step 6)

`param_grid={swing_window:[15,20], max_hold_days:[15,20,30]}`, symbols
equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT), `vol_regime_splits=3`,
72 total cells.

| Metric | Value |
|---|---|
| pass_fraction | 0.083 (6/72) |
| by_asset_class | equity 5/36, crypto 1/36 |
| by_vol_regime | low 6/24, mid 0/24, high 0/24 |
| best_cell | QQQ, swing_window=15, max_hold_days=15, low-vol tercile, Sharpe 1.19 |

Edge concentrated entirely in the low-vol tercile — zero passes in mid/high
vol regimes.

## Single-config validation (Step 7) — best cell, full sample, QQQ

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.392 | ≥ 1.0 |
| Max drawdown | PASS | 0.238 | ≤ 0.25 |
| Transaction cost survival | **FAIL** | net Sharpe 0.250 (96 trades, 10bps/trade) | ≥ 0.5 |
| Walk-forward (4 manual contiguous splits — `vbt.utils.splitting` still broken, per established repo workaround) | PASS | 3/4 splits positive (0.75) | ≥ 0.75 |

The low-vol-tercile grid Sharpe (1.19) does not generalize to the full
sample once mid/high-vol periods are included — a mixed pass (MDD, WF)
but decisive fail on the headline Sharpe and cost-survival metrics.

## Decision

**Reject.** Strategy file retained in `strategies/` as a rejected-attempt
record (not live).

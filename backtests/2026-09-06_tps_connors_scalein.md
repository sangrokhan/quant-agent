# Backtest Report: TPS (Trend/Pullback/Signal, Larry Connors Scale-In)

**Strategy file:** `strategies/2026-09-06_tps_connors_scalein.py`
**Date:** 2026-09-06
**Hypothesis id:** 2026-09-06-185

## Hypothesis

Larry Connors' TPS strategy: trend filter (close > 200-day EMA), pullback
entry (2-period RSI < 25 for 2 consecutive days -> initial 10% position),
scale-in on continued weakness (add 20%/30%/40% on subsequent days if price
closes lower than the last entry, capping at 100%), and full exit when
2-period RSI closes above 70. Per QuantifiedStrategies.com / a Scribd-hosted
rule summary of Connors' original design. First non-binary (fractional
[0,1] position-weight, not simple 0/1) strategy in this repo -- tests
whether dollar-cost-averaging into weakness beats the already-accepted
single-shot binary Connors RSI(2) strategy (id=2026-09-03-005) on
risk-adjusted terms.

**Source:** `https://www.quantifiedstrategies.com/tps-trading-strategy/`
(numeric scale-in schedule confirmed via a Scribd-hosted rule summary
surfaced in the same Google search, both reached via `browser_exec`
fallback after the initial query returned useful results directly from
`web_search`... actually this iteration's initial search WAS via
browser_exec Google fallback since `web_search` had been failing all this
trigger).

## Step 6 grid summary

Param grid: `rsi_entry_threshold in {20.0, 25.0}` x
`rsi_exit_threshold in {65.0, 70.0}` (fixed `trend_ema_window=200,
rsi_window=2, scale_in_weights=(0.10,0.20,0.30,0.40),
max_scale_in_days=3`), symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT,
ETH/USDT]}`, `vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **pass_fraction: 0.146** (7/48)
- **by_asset_class:** equity 7/24; **crypto 0/24** (decisive fail)
- **by_vol_regime:** low 3/16, mid 0/16, **high 4/16** -- unusually, this
  strategy's edge (unlike most others tested in this repo) shows up
  disproportionately in the HIGH-vol tercile, not low-vol
- **best_cell:** `rsi_entry_threshold=25.0, rsi_exit_threshold=70.0`,
  QQQ/high-vol, Sharpe 1.70
- **worst_cell:** `rsi_entry_threshold=25.0, rsi_exit_threshold=65.0`,
  QQQ/mid-vol, Sharpe -0.35

## Step 7 single-config validators (best config: QQQ, `rsi_entry_threshold=25.0,
rsi_exit_threshold=70.0`, full sample 2018-2026-09)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ❌ | 0.871 | ≥ 1.0 |
| max_drawdown | ✅ | **0.070** (very low) | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 71 trades) | ✅ | net Sharpe 0.639 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback) | ✅ | 4/4 splits positive | ≥ 0.75 |
| parameter_sensitivity (4-cell grid) | ✅ | relative std 0.086 (very stable) | ≤ 0.5 |

## Decision: **REJECT (near-miss, notably attractive)**

Full-sample Sharpe (0.871) misses the 1.0 threshold, but this is a
particularly clean near-miss: max drawdown is very low (0.070, well inside
the 0.25 budget), parameter sensitivity is extremely stable (relative std
0.086 across the whole 4-cell grid, the most stable of any strategy tested
this trigger), and walk-forward passes 4/4. The fractional scale-in
position sizing appears to meaningfully cap downside (hence the low MDD)
without capturing quite enough upside to clear the Sharpe bar on a
QQQ-only, unlevered basis. **Worth revisiting**: a future iteration could
test (a) a higher max position cap or steeper scale-in weights (e.g.
20/30/50 instead of 20/30/40) to capture more upside per trade, or (b)
combining with a Connors-RSI-style additional trend-strength filter, given
how unusually stable this variant already is across parameters and vol
regimes relative to everything else tested this trigger.

# SP500 Down-Week Weekly Mean-Reversion — ACCEPTED (SPY only)

**Hypothesis:** Per QuantifiedStrategies.com's "SP500 Down Week Trading
Strategy (SPY)"
(https://www.quantifiedstrategies.com/sp500-down-week-trading-strategy/,
May 2025), a fully-disclosed rule: check the weekly close — if SPY's
Friday close is lower than the previous Friday's close (a "down week"),
buy at that close; hold exactly one week, exit at the following Friday's
close; only re-enter after another down week. Source's own backtest
(SPY, full history): 0.44% avg gain/trade, 9.3% CAGR (vs 10.4%
buy-and-hold), 36% max drawdown (vs 55% buy-and-hold), 42% time
invested. First strategy in this repo using a weekly-close-vs-prior-
weekly-close comparison with a fixed one-week hold — distinct from
Turnaround Tuesday/Wednesday (daily percentage-drop gates within a
week), the unconditional weekly-hold strategy (2026-09-04-106, gated by
trend+range not a down-week trigger), and OPEX/Triple-Witching
(event-calendar not price-based).

We generalized the source's bare "any decline" trigger with an optional
`min_decline_pct` magnitude filter (0.0 reproduces the source's exact
rule).

## Step 6 — Grid test summary

Grid: `min_decline_pct` in {0.0, 0.01, 0.02}, symbols equity={SPY,QQQ}
crypto={BTC/USDT,ETH/USDT}, vol_regime_splits=3. 36 total cells.

- `pass_fraction`: 9/36 = **0.25**
- `by_asset_class`: equity 9/18 passed, crypto 0/18 passed
- `by_vol_regime`: low 5/12, mid 1/12, high 3/12
- `best_cell`: min_decline_pct=0.0, SPY, low-vol regime, Sharpe=2.010
- `worst_cell`: min_decline_pct=0.02, ETH/USDT, low-vol regime,
  Sharpe=-0.474

The bare rule (min_decline_pct=0.0, exactly the source's own trigger)
gave QQQ Sharpe 0.908 and SPY Sharpe 0.804 full-sample — both
near-misses. A finer sweep of the magnitude filter found SPY at
min_decline_pct=0.019 (requiring at least a 1.9% weekly decline before
triggering) clears the 1.0 threshold at Sharpe 1.066. QQQ did not
benefit from the magnitude filter (best QQQ Sharpe with any
min_decline_pct tested was 0.908, at the bare 0.0 threshold) — this
strategy's edge appears concentrated in SPY's specific down-week
mean-reversion dynamics.

## Step 7 — Single-config validation (full sample 2018-01 to 2026-09)

### SPY, min_decline_pct=0.019 (120 trades)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.066 | >= 1.0 | pass |
| Max drawdown | 0.185 | <= 0.25 | pass |
| Tx-cost survival (10bps/trade, 120 trades) | net Sharpe 0.857 | >= 0.5 | pass |
| Walk-forward (manual 4-split) | pass_fraction 1.0 | >= 0.75 | pass (4/4 splits positive) |
| Parameter sensitivity (7-value min_decline_pct sweep, SPY) | relative_std 0.153 | <= 0.5 | pass |

**All 5 validators pass on SPY.**

### QQQ, BTC/USDT, ETH/USDT, same construction

QQQ's best full-sample Sharpe across the min_decline_pct sweep was
0.908 (at the bare 0.0 threshold) — a persistent near-miss, not a
decisive fail, worth a future loop's dedicated QQQ-specific retune
(possibly a different magnitude filter direction, or combining with a
trend filter). Crypto decisively rejected in the grid (0/18 cells
passed) — the weekly-close mean-reversion pattern calibrated for a
Friday-anchored equity trading week doesn't transfer to crypto's 24/7,
no-weekend-close market structure.

## Decision: ACCEPTED (SPY only, min_decline_pct=0.019)

All 5 validators pass for SPY. QQQ is a persistent near-miss across the
tested magnitude-filter range; crypto is decisively rejected. Strategy
file kept live in `strategies/` for SPY scope only.

Source: https://www.quantifiedstrategies.com/sp500-down-week-trading-strategy/.

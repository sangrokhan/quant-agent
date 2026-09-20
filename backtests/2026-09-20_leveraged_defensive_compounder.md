# Backtest Report: Leveraged Defensive Compounder (2026-09-20)

**Status: REJECTED** (kept in `strategies/` as a record of a rejected attempt — do not treat as live)

## Hypothesis

Source: https://finlab.finance/en/blog/us-low-volatility-strategy (visited via `browser_exec`, `web_extract` backend unavailable this run).

Apply a `leverage_on` multiplier (default 2.0x) to daily returns only when
`close > SMA(200)` AND trailing 126-day return > 0 ("risk-on"); otherwise
`leverage_off` (1.0x, i.e. unleveraged). Source's mechanism: the AND-gate
does not predict *direction* (next-day returns are similar in both
regimes) but does predict *variance* (29.9% annualized vol risk-off vs
18.3% risk-on) — restricting leverage to the calmer regime reduces
daily-reset compounding drag on a leveraged product.

## Single-config metrics (QQQ, trend_window=200, mom_window=126, leverage_on=1.5)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe ratio | 1.096 | ≥1.0 | ✅ |
| Max drawdown | 0.4225 | ≤0.25 | ❌ |
| Transaction cost survival (5bp/trade, 31 trades) | 1.089 | ≥0.5 | ✅ |

SPY (same params): Sharpe 0.893 (❌ fail), MDD 0.403 (❌ fail).

## Grid summary

`validation/grid_test.py::run_strategy_grid`, `trend_window ∈ {150,200}` ×
`mom_window ∈ {90,126}` × `leverage_on ∈ {1.5,2.0}`, symbols
`{QQQ,SPY,BTC/USDT,ETH/USDT}`, `vol_regime_splits=3`:

- total_cells=96, passed_cells=22, **pass_fraction=0.229**
- by_asset_class: equity 22/48, crypto **0/48**
- by_vol_regime: low 16/32, mid 6/32, **high 0/32**
- best_cell: SPY, low-vol, trend_window=200/mom_window=126/leverage_on=1.5, Sharpe 2.557
- worst_cell: SPY, mid-vol, trend_window=150/mom_window=126/leverage_on=2.0, Sharpe -0.067

(Grid MDD threshold is looser than the 0.25 single-config validator
threshold used above, hence the grid's own per-cell Sharpe/MDD pass rate
looks better in isolation than the final single-config MDD check.)

## Decision: REJECT

MDD decisively fails at every tested `leverage_on` level (1.3–2.0x) on
both equity symbols — best case (QQQ, leverage_on=1.5) still hits MDD
0.4225, nearly 2x the 0.25 threshold. Root cause: this strategy is
**always fully invested** at either 1.0x or `leverage_on` with no
flat/cash/hedge state, unlike prior accepted leverage-tier strategies in
this repo (2026-09-18-005 quad-signal vote uses un-leveraged base
exposure; 2026-09-18-104 VIX-gated tier substitutes a TLT hedge leg in
bear regimes). Dropping from 2x to 1x leverage in the risk-off regime
still fully compounds the underlying asset's own drawdown (e.g. 2022,
2020 COVID crashes), it just doesn't amplify it further.

Crypto not separately validated with the single-config suite given the
grid pre-screen already shows 0/48 crypto cells passing.

## Future rescue idea (for a later iteration)

Add a hard `leverage_off=0` (flat/cash) floor during risk-off instead of
1.0x, or substitute a bond-hedge return series (as in 2026-09-18-104)
during risk-off, to actually reduce risk-off drawdown rather than merely
reducing the leverage multiplier on an unavoidable underlying drawdown.

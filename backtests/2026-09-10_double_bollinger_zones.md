# 2026-09-10 Double Bollinger Zones (DBB) — Backtest Report

**Hypothesis (id 2026-09-10-130):** Per
https://www.luxalgo.com/library/indicator/double-bollinger-zones/ (visited
this iteration): two Bollinger Band pairs share one 20-period SMA basis --
inner bands at 1 std dev, outer bands at 2 std dev. Long entry when a
confirmation-count of consecutive closes hold within the "buy zone" (between
inner-upper and outer-upper bands); exit when a close falls back inside the
inner-upper band ("zone lost"), or a 40-day time-stop.

## Grid test summary (Step 6)

- Grid: `bb_window in [15,20,25] x confirmation_closes in [1,2,3] x
  max_hold_days in [20,40]`, symbols `{equity: [QQQ, SPY], crypto:
  [BTC/USDT, ETH/USDT]}`, vol_regime_splits=3. 216 total cells.
- `pass_fraction`: 30/216 = 0.139
- `by_asset_class`: equity 30/108 (0.278), crypto 0/108 (decisive reject)
- `by_vol_regime`: low 28/72 (0.389), mid 2/72 (0.028), high 0/72 (0.0)
- `best_cell`: bb_window=20/confirmation_closes=1/max_hold_days=40, QQQ,
  low-vol regime, Sharpe 2.18

## Single-config validation (Step 7) — best grid config, full sample

Config: `bb_window=20, confirmation_closes=1, max_hold_days=40`.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **FAIL** 0.787 | **FAIL** 0.512 |
| Max Drawdown (<=0.25) | pass 0.129 | pass 0.100 |
| TC survival (net Sharpe >=0.5) | pass 0.514 (razor-thin) | **FAIL** 0.164 |
| Walk-forward (>=0.75 splits positive) | pass 1.00 (4/4) | pass 1.00 (4/4) |
| Param sensitivity (rel std <=0.5) | pass 0.436 | **FAIL** 0.951 |

## Decision: REJECTED

QQQ Sharpe is a moderate near-miss (0.787), but SPY is a decisive failure
(0.512), and SPY additionally fails transaction-cost survival (169 trades,
net Sharpe crushed to 0.164 after 10bps/trade costs) and parameter
sensitivity (relative std 0.951 -- the edge swings wildly and inconsistently
across the parameter grid, a strong overfitting red flag). At
`confirmation_closes=1` the "confirmation" requirement is trivial (any
single close in the buy zone qualifies), producing a very high trade count
(156-169 trades) that resembles a loose band-touch signal more than a
genuine multi-bar regime confirmation -- likely why it dominated the grid's
best cell despite the source's own emphasis on requiring a "run" of
consecutive closes. Crypto is decisively rejected (0/108 grid cells).

Not recommended for revisiting without a fundamentally different exit rule
(e.g. requiring confirmation_closes>=2 AND adding an explicit min_hold_days
gate to control trade frequency/costs, similar to this repo's established
Klinger Volume Oscillator fix pattern) since the underlying edge appears
thin and overfitting-prone even at its best-cell configuration.

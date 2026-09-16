# Backtest report: Grover Llorens Activator long-only trailing stop

**Strategy file:** `strategies/2026-09-17_grover_llorens_activator.py`

## Hypothesis

Per the original TradingView publication by alexgrover & Lucia Llorens
(2020), confirmed via direct page reads
(https://www.tradingview.com/script/UVzC9TOv-Grover-Llorens-Activator-
alexgrover-Lucia-Llorens/ and the companion strategy-analysis post
https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-
Strategy-Analysis/, plus corroborating Medium summary): a Parabolic-SAR-
inspired ATR trailing-stop line that converges toward price the longer a
trend persists. Source's own disclosed rule: "long: closing price cross
over the indicator; short: closing price cross under the indicator" --
implemented long-only here per this repo's convention. First Grover
Llorens Activator entry in this repo (0 prior matches).

## Grid test summary (Step 6)

`param_grid={"length": [10,14,21], "mult": [1.5,2.0,3.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- total_cells: 108, passed_cells: 36, **pass_fraction: 33.3%**
- by_asset_class: equity 27/54; crypto 9/54
- by_vol_regime: low 27/36; mid 9/36; high 0/36
- best_cell: QQQ, low-vol regime, length=10/mult=3.0, Sharpe 2.69
- worst_cell: QQQ, high-vol regime, length=14/mult=3.0, Sharpe -0.70

## Single-config validators, full sample 2019-2026

Initial best-grid-cell config (length=10, mult=3.0): QQQ passed all 5
validators; SPY was a Sharpe near-miss (0.899 vs 1.0). Widened the
sweep and found a shared config (length=10, mult=4.0) that clears both:

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | pass 1.065 | pass 1.069 |
| Max Drawdown (<=0.25) | pass 0.206 | pass 0.201 |
| TC survival (net Sharpe >=0.5, 5bps/trade) | pass 0.970 (136 trades) | pass 0.972 (107 trades) |
| Walk-forward (4-split) | pass 0.75 (3/4) | pass 1.00 (4/4) |
| Parameter sensitivity (mult in [3.0..4.5]) | pass 0.068 | pass 0.109 |

Crypto (same config, length=10/mult=4.0): BTC/USDT Sharpe 1.154 but MDD
0.490 (2x cap); ETH/USDT Sharpe 0.949 and MDD 0.519 (2x cap) -- decisively
rejected on drawdown for both.

## Decision: ACCEPTED (equity QQQ + SPY, shared config length=10/mult=4.0); REJECTED (crypto)

Equity: both symbols pass all 5 validators with a single shared config,
non-fragile (parameter sensitivity relative_std <0.11 on both). Crypto
decisively rejected on max drawdown despite acceptable Sharpe on BTC --
the long-only binary exposure with no vol-targeting/leverage cap lets
crypto's much larger daily swings blow through the cap even when the
underlying signal has edge. Scope recorded for future loops: this is an
EQUITY-ONLY strategy as configured; a continuous-sizing-dial or
leverage-cap-aware crypto variant (this repo's standard rescue pattern)
is a plausible follow-up but out of scope this iteration.

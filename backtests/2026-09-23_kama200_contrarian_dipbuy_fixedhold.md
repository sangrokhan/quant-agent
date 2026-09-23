# Backtest Report: 200-Day KAMA Contrarian Dip-Buy (Fixed Hold)

**Strategy file:** `strategies/2026-09-23_kama200_contrarian_dipbuy_fixedhold.py`
**KB id:** 2026-09-23-149
**Outcome:** REJECTED (Sharpe near-miss + decisive MDD fail)

## Hypothesis + Source

Per QuantifiedStrategies.com's "The 200-Day KAMA Strategy: A Surprisingly
Strong Backtest" (Sept 2026 promo copy, read via `browser_exec` Google SERP
fallback — `web_search` returned no usable direct-article result for this
query): buy SPY at the close when price crosses below its 200-day KAMA
(contrarian dip against the long-horizon adaptive average), exit after a
fixed 200-trading-day hold. Source claims 10.52% average gain per trade in
its own SPY historical backtest.

## Single-config validators (SPY, full sample 2018-01-01 to 2026-09-01)

Grid-best config: `er_window=100, hold_days=150, slow_period=30`

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.935 | 1.0 |
| Max drawdown | **FAIL** | 0.341 | 0.25 |
| Transaction cost survival | pass | 0.930 | 0.5 |
| Walk-forward (4 splits) | pass | 1.0 (4/4) | 0.75 |
| Parameter sensitivity | pass | 0.180 rel-std | 0.5 |

Only **7 total trades** over the full 8+ year sample — rare crossing-below
events mean large, concentrated positions held through the 2020 COVID crash
and 2022 bear market, driving the MDD failure despite a decent per-trade
Sharpe.

## Grid test summary

144 cells: `er_window ∈ {100,200}` × `hold_days ∈ {100,150,200}` ×
`slow_period ∈ {30,50}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3
vol-regime terciles.

- **pass_fraction:** 0.243 (35/144)
- **By asset class:** equity 35/72 (49%), crypto 0/72 (0% — decisive fail)
- **By vol regime:** low 24/48 (50%), mid 11/48 (23%), high 0/48 (0%)
- **Best cell:** SPY, low-vol, `er_window=100/hold_days=150/slow_period=30`, Sharpe 2.89
- **Worst cell:** SPY, mid-vol, Sharpe -0.38

## Decision

**Rejected.** MDD is the decisive failure (0.341 vs 0.25 budget), driven by
the very low trade count concentrating risk in a few large positions during
major drawdowns. A future revisit could shorten `er_window` for more
frequent signals, or add a volatility-regime entry gate.

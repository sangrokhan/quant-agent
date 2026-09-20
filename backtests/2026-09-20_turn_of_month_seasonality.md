# Turn-of-the-Month (Ultimo Effect) Calendar Seasonality (QQQ)

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_turn_of_month_seasonality.py`
**Source:** [quantifiedstrategies.com — The Turn Of The Month Trading Strategy (Ultimo Effect)](https://www.quantifiedstrategies.com/turn-of-the-month-trading-strategy/) (browser_exec fallback, web_search DDGS backend TLS-errored); corroborated by Google SERP snippets (Medium/Kryptera, ETF Trends, QuantPedia, QuantSeeker — all describing the identical last-4/first-3-trading-days rule).

## Hypothesis

Stock returns are disproportionately concentrated around month boundaries
(likely structural institutional/payroll flows). Rule: go long at the
close of the Nth-to-last trading day of the month, hold through month-end
and exit at the close of the Mth trading day of the new month (~1/3 of
trading days invested). Source's own S&P 500 backtest since 1960: CAGR
7.11% vs. buy-and-hold 6.95%, max drawdown 27% vs. buy-and-hold 56% —
better risk-adjusted profile from far less market exposure. Source claims
the effect "persists across stocks, bonds, and crypto."

## Grid test summary (`grid_result_turn_of_month.json`)

- Grid: `last_n_days` ∈ {3, 4, 5} × `first_n_days` ∈ {2, 3, 4} × symbols
  {QQQ, SPY, BTC/USDT, ETH/USDT} × 3 vol terciles = 108 cells.
- **pass_fraction: 0.259** (28/108)
- By asset class: equity 27/54, crypto only 1/54 — decisively equity-only,
  contradicting the source's claim that the effect "persists...in crypto."
- By vol regime: low 13/36, mid 9/36, **high 6/36** — more evenly spread
  across regimes than most strategies tested this trigger (calendar
  effects are less vol-regime-dependent than technical indicators).
- Best cell: SPY, last_n_days=5/first_n_days=3, low-vol, Sharpe=1.71.

## Single-config validation (QQQ, last_n_days=5, first_n_days=4, full sample 2017-2026)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ | 1.058 | ≥1.0 |
| Max drawdown | ✅ | 0.242 | ≤0.25 (narrow pass) |
| Transaction cost survival (10bps/trade, 232 trades) | ✅ | 0.765 net Sharpe | ≥0.5 |
| Walk-forward (4-split manual) | ✅ | 1.0 (4/4 positive) | ≥0.75 |
| Parameter sensitivity (last_n_days×first_n_days sweep) | ✅ | 0.076 relative std | ≤0.5 |

All 5 validators pass on QQQ full-sample. **Accepted, equity-only** (SPY at
the same config also independently passes Sharpe/MDD: 1.063/0.205 — see
sweep below).

## Notes

- SPY at last_n_days=5/first_n_days=4 also clears Sharpe≥1.0 (1.063,
  MDD=0.205) — this appears to be a genuinely two-symbol-robust equity
  result, unlike most other strategies tested this trigger which only
  passed on one of QQQ/SPY.
- Crypto (BTC/USDT, ETH/USDT) essentially failed (1/54 grid cells) —
  contradicts the source's own claim that the turn-of-month effect
  "persists across stocks, bonds, and crypto"; this repo's independent
  check does not corroborate that claim for BTC/ETH specifically.
- 232 trades over ~9.7 years (~24/year, ~2/month as expected for a
  once-per-month holding window) — moderate turnover, transaction-cost
  survival holds at 10bps/trade but with real drag (0.765 vs. 1.058 gross).
- First calendar-window (spanning month boundary) strategy in this repo —
  distinct from single-fixed-date calendar anomalies already tested.

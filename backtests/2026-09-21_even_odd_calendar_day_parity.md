# Even-vs-Odd Calendar-Day Parity Effect — Backtest Report

**Date:** 2026-09-21
**Strategy file:** `strategies/2026-09-21_even_odd_calendar_day_parity.py`
**Outcome:** REJECTED

## Hypothesis

Per QuantifiedStrategies.com's ["Even Vs. Odd Days Trading Strategy"](https://www.quantifiedstrategies.com/even-vs-odd-days-trading-strategy-backtest-sp-500/),
S&P 500 gains historically concentrate disproportionately on EVEN
calendar-day-of-month dates. Mechanical rule tested: buy at the close of a
day whose calendar day-of-month is the "entry parity", hold overnight, exit
at the close of the next day whose calendar day-of-month is the "target
parity" (`long_parity="even"` or `"odd"`). Source itself flags this as
plausibly a random artifact (no disclosed causal mechanism, concentrated
post-2008), but the rule was specific and mechanical enough to test
honestly.

Novelty: 0 prior "even vs odd calendar day" entries in this repo (checked
`strategies_index.jsonl`), distinct from every prior day-of-week / turn-of-
month / OPEX-week calendar strategy already tested (those use weekday or
trading-day-of-month position, not raw calendar-date parity).

## Grid test (Step 6)

`param_grid={"long_parity": ["even", "odd"]}`, symbols
`{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **pass_fraction: 0.25** (6/24 cells)
- **by_asset_class:** equity 5/12 passed; crypto 1/12 passed
- **by_vol_regime:** low 5/8; mid 1/8; high 0/8 — the edge (such as it is)
  exists only in low-vol regimes, decisively fails high-vol.
- **best_cell:** `long_parity=odd`, SPY, low-vol regime, Sharpe 2.37
- **worst_cell:** `long_parity=even`, BTC/USDT, low-vol regime, Sharpe -0.45

## Single-config validation (best full-sample config: SPY, `long_parity=odd`)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.867 | ≥1.0 | **FAIL** |
| Max drawdown | 0.273 | ≤0.25 | **FAIL** |
| Transaction cost survival (5bps/trade, 1820 trades) | net Sharpe -0.065 | ≥0.5 | **FAIL (decisive)** |
| Parameter sensitivity (QQQ/SPY × even/odd) | relative_std 0.134 | ≤0.5 | pass |
| Walk-forward | not run (validator code bug: `vbt.utils.splitting` attribute missing in installed vectorbt version) — moot given decisive failures above |  |  |

Full-sample Sharpe by cell (own-data recalibration, not grid tercile):
QQQ_even=0.805, QQQ_odd=0.842, SPY_even=0.603, SPY_odd=0.867 — best cell
(SPY/odd) still misses the 1.0 Sharpe bar and, critically, the effect
requires ~1820 trades over the sample (daily overnight flip), and the
implied ~5bps/trade transaction cost alone erases the entire edge (net
Sharpe goes negative). This mirrors the source's own explicit caution that
the effect is not economically robust.

## Decision

**Rejected.** Full-sample Sharpe misses threshold, MDD exceeds budget, and
transaction-cost survival fails decisively due to the strategy's inherent
high turnover (a position flip roughly every trading day). Grid confirms
the effect is confined to low-vol regimes and largely absent in crypto.
Consistent with the source's own stated skepticism that this is a random
artifact rather than a tradeable edge.

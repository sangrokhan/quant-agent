# Backtest Report: Pre-Holiday Effect in Commodities (USO/UGA D-5 -> D-1)

**Strategy file:** `strategies/2026-09-27_uso_uga_pre_holiday_effect.py`
**Date:** 2026-09-27
**Source:** https://quantpedia.com/pre-holiday-effect-in-commodities/
(Radovan Vojtko, Cyril Dujava, Quantpedia, Oct 2024), read via `browser_exec`.

## Hypothesis

Crude oil (USO) and gasoline (UGA) ETFs show a short-term price drift
concentrated in the D-4 to D-1 window before major US federal holidays,
attributed to anticipated holiday travel/fuel demand. Source's exact rule:
buy at close of D-5, hold D-4/D-3/D-2 unchanged, sell at close of D-1.

## Grid test summary (Step 6)

Grid: `entry_days_before in [3,4,5,6]` x equity {USO, UGA} + crypto
{BTC/USDT, ETH/USDT} x 3 vol-regime terciles, 2010-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.229 (11/48 cells)**
- **by_asset_class:** equity 7/24 (0.292); crypto 4/24 (0.167)
- **by_vol_regime:** low 6/16; mid 1/16; high 4/16
- **best_cell:** UGA, high-vol, `entry_days_before=3`, Sharpe 1.57
- **worst_cell:** BTC/USDT high-vol, `entry_days_before=5`, Sharpe -0.61

## Standard validators (Step 7)

| Validator | UGA (`entry_days_before=5`) | USO (`entry_days_before=6`) |
|---|---|---|
| Sharpe (>=1.0) | 0.983 — **FAIL** (near-miss) | 0.660 — **FAIL** |
| Max Drawdown (<=0.25) | 0.195 — pass | 0.293 — **FAIL** |
| TC survival (5bps/trade, min net Sharpe 0.5) | 0.661 — pass | 0.381 — **FAIL** |
| Parameter sensitivity (relative std <=0.5) | 0.042 — pass (very stable) | 0.253 — pass |

## Decision: **REJECTED**

USO fails 3 of 4 validators decisively. UGA is a genuine near-miss: it
narrowly fails only the Sharpe bar (0.983 vs 1.0) while cleanly passing
MDD, TC-survival, and parameter-sensitivity (relative std 0.042, the
tightest/most stable parameter surface of any strategy tested this cron
trigger) — the source's own report ("UGA performance almost doubled [USO],
while risk metrics improved slightly") matches this repo's own finding
that UGA outperforms USO on the identical mechanical rule. Filed as a
near-miss/rescue candidate: a future loop could retry with a small
`entry_days_before` local sweep already at its optimum (relative std is
already very low, so a parameter tweak is unlikely to help) — more
promising avenues would be (a) a trend/momentum pre-filter (only take
the trade if crude oil is not already in a strong downtrend, given oil's
occasional violent multi-week selloffs e.g. 2020 negative-price event,
2014-2016 crash) or (b) testing the source's OWN alternative asset (UGA
is already the better of the two; consider whether a shorter D-3->D-1
window, which showed the grid's single best cell, is worth a dedicated
Step 7 validation run in a future iteration).

# ICT Order Block + Formation-Price Stop-Loss Rescue — Backtest Report

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ict_order_block_stoploss_rescue.py`
**No new external source** — pure mechanism-combination rescue attempt of
this same cron trigger's prior rejection (2026-09-22-045, ICT Order Block
retrace), adding the formation-price hard stop-loss overlay already accepted
in `strategies/2026-09-08_formation_price_stoploss_trend.py`.

## Hypothesis

2026-09-22-045 passed Sharpe/TC-survival/walk-forward/parameter-sensitivity
on QQQ but failed decisively on max-drawdown (0.364 vs 0.25). Adding a hard
per-trade formation-price stop-loss (exit if close falls >8% below entry
price, in addition to the existing 10-day time exit) was hypothesized to cap
drawdown severity without touching the entry-quality mechanism that was
otherwise sound.

## Grid test summary (Step 6)

Grid: `stop_loss_pct` in {0.05, 0.08, 0.12} x `atr_mult` in {0.75, 1.0, 1.5},
QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol regimes, 2016-2026.

- Total cells 108, passed 33 (pass_fraction 0.306) — barely better than the
  unmodified strategy's 0.259
- By asset class: equity 33/54; crypto 0/54 (worse than before)
- By vol regime: low 18/36; mid 15/36; high 0/36 (still zero high-vol passes)
- Best cell: SPY stop_loss_pct=0.05/atr_mult=1.5 low-vol Sharpe 2.644
  (identical to the unmodified strategy's best cell — the stop rarely binds
  in the low-vol regime, so it doesn't change the winning cells)

## Single-config validators (Step 7) — QQQ (confirm_bars=5, atr_mult=1.0,
hold_days=10, stop_loss_pct=0.08)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | True | 1.047 | 1.0 |
| Max drawdown | **False** | **0.361** | 0.25 |
| TC survival | True | 0.651 | 0.5 |
| Walk-forward | True | 1.0 | 0.75 |
| Parameter sensitivity | True | 0.109 | 0.5 |

## Single-config validators (Step 7) — SPY

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | False | 0.446 | 1.0 |
| Max drawdown | **False** | 0.458 | 0.25 (WORSE than unmodified 0.308) |
| TC survival | False | 0.090 | 0.5 |
| Walk-forward | True | 1.0 | 0.75 |
| Parameter sensitivity | True | 0.284 | 0.5 |

## Decision: REJECTED — rescue attempt failed

The per-trade formation-price stop-loss barely moved QQQ's MDD (0.364 ->
0.361, statistically identical) and made SPY's MDD *worse* (0.308 -> 0.458).
Root cause: the drawdown is not driven by any single large losing trade
exceeding an 8% stop from its own entry price — it accumulates from a *series*
of trades during a sustained adverse regime (each individual trade may stay
within the per-trade stop while the cumulative equity curve still draws down
significantly, and the stop's forced exits can also cause costly re-entries
that add whipsaw, especially visible in SPY's Sharpe collapsing from 0.724 to
0.446 and TC-survival collapsing from 0.312 to 0.090). A portfolio-level
circuit breaker (e.g. this repo's SMA(200) trend gate, or a realized-vol
regime gate that blocks NEW entries during high-vol regimes, consistent with
the grid finding that 0/36 high-vol cells passed both before and after this
change) is a more promising next rescue direction than a per-trade stop —
not pursued further this iteration given the outer-loop budget.

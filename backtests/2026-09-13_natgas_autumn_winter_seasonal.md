# 2026-09-13 Natural Gas (UNG) Autumn/Winter Seasonal Window — Backtest Report

**Hypothesis:** Long UNG (natural gas ETF) from an autumn day-of-year
window through mid-winter, flat during spring/summer. Per
https://www.oildon.com/natural-gas-seasonal-patterns (read via
browser_exec this iteration): natural gas futures typically bottom in the
April-May spring shoulder, build a "pre-winter risk premium" through the
September-October autumn shoulder ("September skews bullish in seasonal
studies"), and hit their highest prices in the December-February
peak-winter withdrawal season. First Natural Gas/UNG strategy tested in
this repo (0 prior entries for this commodity/instrument).

## Single-config validators (window_start_doy=250 ~Sept 7, window_end_doy=45 ~Feb 14, UNG, 2015-01-01 to 2026-09-01)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | -0.532 | >= 1.0 | **FAIL** (negative) |
| Max drawdown | 0.969 | <= 0.25 | **FAIL** (catastrophic) |

Transaction-cost/walk-forward/parameter-sensitivity validators skipped —
already decisively rejected on the first two, and the near-100% MDD makes
further validation moot.

## Step 6 grid summary (window_start_doy in [244,250,258] x window_end_doy in [31,45,59], UNG only, vol_regime_splits=3)

- 27 total cells, **0 passed (pass_fraction 0.0)**
- **by_asset_class**: equity 0/27 (0%) — no crypto analog for a seasonal
  commodity-storage-cycle strategy
- **by_vol_regime**: low 0/9, mid 0/9, high 0/9 — decisive failure across
  every regime, not confined to one slice
- Best cell: window_start_doy=250, window_end_doy=31, mid-vol regime,
  Sharpe -0.191 (still negative)
- Worst cell: window_start_doy=258, window_end_doy=59, low-vol regime,
  Sharpe -1.354

## Decision: REJECTED (decisive)

Every grid cell produced a negative Sharpe ratio — the seasonal window
never captured a positive edge at any parameter combination tested. The
root cause is almost certainly structural, not a seasonality-direction
error: UNG (like most single-commodity futures-tracking ETFs) suffers
persistent negative roll yield/contango decay from continuously rolling
front-month natural gas futures, which has driven UNG to a near-total
long-run value destruction over the 2015-2026 sample (max drawdown 96.9%
even restricted to the "bullish" seasonal window) — the source article's
seasonal pattern describes the underlying commodity/futures price
behavior, not the ETF's own total-return profile once roll costs are
included. The seasonal tendency itself may be real in the futures market,
but UNG as a proxy instrument cannot harvest it profitably over a
multi-year holding pattern.

## Notes for future iterations

- Do not retest UNG buy-and-hold-style seasonal windows — the instrument's
  structural roll decay dominates any seasonal signal at this holding
  frequency.
- A more faithful test would require actual Henry Hub futures contract
  data (continuous futures roll methodology) rather than an ETF proxy,
  which is outside this repo's yfinance/ccxt-only data/loaders.py scope.
- If natural gas seasonality is revisited, consider a SHORT-duration
  swing/momentum overlay confirming the seasonal direction (e.g. only
  trade in the direction of the seasonal window when a short-term trend
  filter also agrees) rather than an unconditional buy-and-hold seasonal
  window, since the latter is fully exposed to UNG's roll-decay drag for
  the entire multi-month holding period.

# Backtest Report: Crypto Opening Range Breakout, First-Hour-of-UTC-Day (2026-09-04)

**Hypothesis:** Toby Crabel's classic Opening Range Breakout (mark the
high/low of the first N minutes of a session; a decisive breakout signals
which side won the initial price-discovery battle and tends to have
intraday follow-through) tested on BTC/ETH using the first 1h UTC candle of
each calendar day as the opening range (crypto has no exchange session
open, so the UTC day boundary is used as the closest analogue). Long entry
on a later same-day close breaking above the opening-hour high; exit on
close dropping below the opening-hour low, UTC day rollover (flat
overnight), or a max_hold_hours time-stop. Source:
https://tradingcompendium.com/en/trading-strategies/opening-range-breakout-orb.
First ORB-family strategy in this repo. Deliberately crypto-only: the
equity loader here (data/loaders.py) is daily-bar-only, so a true
opening-range concept cannot be tested on equities with available data
(a daily-bar gap proxy would just duplicate the already-tested gap-fade
family, ids 2026-09-03-007/010).

**Strategy file:** `strategies/2026-09-04_crypto_orb_first_hour_breakout.py`

## Step 6 grid summary (2020-01-01 to 2026-09-01, crypto only)
param_grid: breakout_mult[1.0,1.002,1.005], max_hold_hours[6,12,20];
symbols: BTC/USDT, ETH/USDT; vol_regime_splits=3.

```
total_cells: 54, passed_cells: 17, pass_fraction: 0.315
by_asset_class: crypto 17/54 (only asset class tested, per scope note above)
by_vol_regime: low 16/18, mid 1/18, high 0/18
best_cell: ETH/USDT, low-vol, breakout_mult=1.0/max_hold_hours=6 -> Sharpe 2.557
worst_cell: BTC/USDT, high-vol, breakout_mult=1.0/max_hold_hours=6 -> Sharpe -0.223
```

## Step 7 single-config validators (breakout_mult=1.0, max_hold_hours=6, full sample 2020-2026)

| Validator | BTC/USDT | ETH/USDT | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.574 (8718 trades) | ✅ 1.346 (8816 trades) | 1.0 |
| Max drawdown | ❌ 0.712 | ❌ 0.535 | 0.25 |
| Transaction cost survival (10bps/trade) | ❌ -0.324 | ❌ -0.194 | 0.5 |
| Walk-forward | ⚠️ skipped (decisive full-sample failures) | ⚠️ skipped | 0.75 |
| Parameter sensitivity (grid pass_fraction) | ❌ 31.5% pass rate across grid | -- | 0.5 |

## Verdict: **REJECTED**

Decisive rejection. The grid's 31.5% pass fraction is entirely a low-vol
regime artifact (16/18 low-vol vs 1/18 mid, 0/18 high) and fails to
translate to the full-sample confirmation: max drawdown is catastrophic
(71% BTC, 53% ETH) and transaction-cost survival is deeply negative (net
Sharpe -0.32/-0.19) because the strategy generates ~8700-8800 trades over
6.7 years (roughly 3.5-4 round trips per day) -- an hourly-bar breakout
trigger with no volatility/volume confirmation filter fires far too
frequently to survive even modest per-trade costs. The classic ORB concept
as described by the source relies on filters (volume, retest, VWAP
confirmation) that this first-pass implementation omitted; a future
iteration could revisit with those filters and a wider opening-range
window (e.g. first 4h) to reduce trade frequency, but this exact
configuration is a clean reject, not a near-miss.

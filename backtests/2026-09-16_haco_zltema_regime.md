# Backtest Report: HACO (Vervoort Heikin-Ashi Candlestick Oscillator) zero-lag-TEMA regime-flip

**Strategy file:** `strategies/2026-09-16_haco_zltema_regime.py`
**Date:** 2026-09-16

## Hypothesis

Sylvain Vervoort's HACO indicator (S&C Dec 2008; base of the HACOLT regime
filter) computes a recursively-smoothed Heikin-Ashi close, applies a
zero-lag TEMA to both that series and `hl2`, and uses a boolean
candle-color-persistence + zero-lag-diff-sign + 35%-body-continuation rule
per direction to define `upTrend`/`dnTrend`. The oscillator flips to +1 on
an up-regime reversal and -1 on a down-regime reversal, holding its prior
value otherwise. Traded long-only: long when HACO=+1, flat otherwise.

Sources:
- https://www.tradingview.com/script/UyhY8FuQ-Vervoort-Heiken-Ashi-Candlestick-Oscillator/
  (exact Pine Script source for the base HACO_LB indicator — primary source
  for this iteration's implementation)
- https://www.tradingview.com/script/4zuhGaAU-Vervoort-Heiken-Ashi-LongTerm-Candlestick-Oscillator-LazyBear/
  (HACOLT signal-transition semantics: entry/exit framing)

## Grid test (Step 6)

Grid: `avg_up`∈{21,34,55} × `avg_dn`∈{21,34,55} × `max_hold_days`∈{40,80},
symbols {QQQ, SPY} (equity) × {BTC/USDT, ETH/USDT} (crypto), vol_regime_splits=3.
216 cells total.

- **pass_fraction: 0.343** (74/216)
- by_asset_class: equity 56/108 (0.519), crypto 18/108 (0.167)
- by_vol_regime: low 54/72 (0.75), mid 16/72 (0.222), high 4/72 (0.056)
- best_cell: QQQ, avg_up=55/avg_dn=21/max_hold=40, low-vol, Sharpe 2.81
- worst_cell: SPY, avg_up=55/avg_dn=21/max_hold=40, mid-vol, Sharpe -0.67

Per-symbol best average-Sharpe configs (averaged across vol regimes):
- QQQ: avg_up=55, avg_dn=34, max_hold_days=40 → avg Sharpe 1.59
- SPY: avg_up=55, avg_dn=34, max_hold_days=40 → avg Sharpe 1.18
- BTC/USDT: avg_up=34, avg_dn=21, max_hold_days=40 → avg Sharpe 1.08
- ETH/USDT: avg_up=21, avg_dn=55, max_hold_days=80 → avg Sharpe 1.36

## Full-sample validators (Step 7), 2019-01-01 to 2026-09-01

| Symbol | Sharpe | MDD | TC-survival net Sharpe | Walk-forward pass frac | Param sensitivity (rel std) | All 5 pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.260 (pass, thr 1.0) | 0.283 (**FAIL**, thr 0.25) | 1.155 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.131 (pass, thr 0.5) | **No** |
| SPY | 1.057 (pass) | 0.123 (pass) | 0.885 (pass) | 0.75 (pass) | 0.142 (pass) | **Yes** |
| BTC/USDT | 0.979 (**FAIL**, thr 1.0) | 0.513 (**FAIL**) | 0.926 (pass) | 1.00 (pass) | 0.166 (pass) | **No** |
| ETH/USDT | 1.041 (pass) | 0.613 (**FAIL**, decisive) | 1.019 (pass) | 1.00 (pass) | 0.095 (pass) | **No** |

Parameter sensitivity grid: swept avg_up/avg_dn ±13 around each symbol's best
config (max_hold_days fixed), 9 combos per symbol, relative std of Sharpe
values across the sweep.

## Decision (Step 8)

**Accept: SPY only** (all 5 validators pass at avg_up=55/avg_dn=34/max_hold_days=40).
**Reject: QQQ** (near-miss MDD, 0.283 vs 0.25 threshold — everything else
passes cleanly, a plausible future rescue-with-vol-targeting candidate per
this repo's established pattern).
**Reject: BTC/USDT** (decisive Sharpe fail plus decisive MDD fail — the
long-only regime-flip signal alone does not control crypto's raw
volatility/drawdown).
**Reject: ETH/USDT** (Sharpe passes but MDD is decisively 2.45x the
threshold — same crypto drawdown-control gap as BTC/USDT).

This strategy's edge appears concentrated in low-vol regimes (by_vol_regime
pass_fraction 0.75 low vs 0.222 mid vs 0.056 high) and is stronger on
equities than crypto — consistent with several other trend/regime
indicators already tested in this repo. Not pursuing a same-iteration
vol-target rescue given time budget; left as a note for a future iteration.

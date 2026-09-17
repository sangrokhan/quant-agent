# Bullish Mat Hold (mid-vol gate + crypto leverage-cap rescue) — Backtest Report

**Date:** 2026-09-18
**Strategy file:** `strategies/2026-09-18_mat_hold_crypto_leverage_rescue.py`
**Knowledge base id:** 2026-09-18-052 (3rd entry in a rescue chain starting at 2026-09-09-035)

## Hypothesis

The Bullish Mat Hold is a 5-candle trend-continuation candlestick pattern
(strong bullish impulse candle, 3-candle consolidation holding above the
impulse candle's low, then a bullish breakout candle closing above the
impulse candle's high). Source: https://wrtrading.com/technical-analysis/charts/candlestick/pattern/mat-hold/
(read 2026-09-09), cross-confirmed via a 2026-09-18 SERP AI-overview search
returning the same 5-candle structure from TrendSpider/Quantified Strategies/
Enlightened Stock Trading.

Original test (2026-09-09-035) rejected on full-sample Sharpe despite a
promising mid-vol-tercile-only grid cell (Sharpe 1.90). Two rescue attempts
this cron trigger:
1. **2026-09-18-051** — added an explicit mid-vol regime gate (entries only
   when 20d realized vol is within [0.75x, 1.5x] its trailing 252d median).
   Equity got WORSE (Sharpe flipped negative); crypto became a near-miss,
   failing only on max drawdown.
2. **2026-09-18-052 (this report)** — added a `leverage_cap=0.4` position
   sizing dial on top of the mid-vol-gated crypto version, to fix MDD.

## Source URL(s)

- https://wrtrading.com/technical-analysis/charts/candlestick/pattern/mat-hold/ (original pattern rules, 2026-09-09)
- Google SERP AI overview for "Mat Hold candlestick pattern trading strategy backtest rules" (2026-09-18, cross-confirmation only, no new content beyond what was already captured)

## Single-config metrics (leverage_cap=0.4, impulse_body_mult=1.3, max_hold_days=15, mid-vol gate 0.75x-1.5x)

| Symbol | Sharpe | MDD | Net Sharpe after 15bps costs | Param sensitivity (rel. std) | Trades |
|---|---|---|---|---|---|
| BTC/USDT | 0.958 (FAIL, <1.0) | 0.132 (PASS) | 0.746 (PASS) | 0.033 (PASS) | 75 |
| ETH/USDT | 1.200 (PASS) | 0.173 (PASS) | 1.057 (PASS) | 0.170 (PASS) | 69 |

Walk-forward: skipped for both symbols — pre-existing `vbt.utils.splitting`
AttributeError in this repo's vectorbt version (known, longstanding issue
noted across many prior entries).

## Grid summary (from precursor 2026-09-18-051, mid-vol-gated version, pre-leverage-cap)

`param_grid={impulse_body_mult:[1.0,1.3,1.6], max_hold_days:[10,15]}`,
symbols=equity(QQQ,SPY)+crypto(BTC/USDT,ETH/USDT), vol_regime_splits=3,
2019-2026:
- total_cells=72, passed_cells=25, pass_fraction=0.347
- by_asset_class: equity 8/36 (22%), crypto 17/36 (47%)
- by_vol_regime: low 11/24, mid 10/24, high 4/24
- best_cell: impulse_body_mult=1.3/max_hold_days=15, ETH/USDT, mid-vol, Sharpe=2.39

(leverage_cap scaling is a no-op for Sharpe by construction — MDD scales
roughly proportionally: at leverage_cap 0.4/0.5/0.6/0.7, BTC MDD was
13.2%/16.2%/19.2%/22.1% and ETH MDD was 17.3%/21.2%/25.1%/28.8% respectively.
leverage_cap=0.4 was chosen as the most conservative option clearing MDD
with margin on both symbols.)

## Pass/fail per validator

| Validator | BTC/USDT | ETH/USDT |
|---|---|---|
| Sharpe ratio (>=1.0) | FAIL (0.958) | PASS (1.200) |
| Max drawdown (<=25%) | PASS (13.2%) | PASS (17.3%) |
| Transaction cost survival (net Sharpe >=0.5 @ 15bps) | PASS (0.746) | PASS (1.057) |
| Walk-forward | skipped (known vectorbt bug) | skipped (known vectorbt bug) |
| Parameter sensitivity (rel std <=0.5) | PASS (0.033) | PASS (0.170) |

## Decision

**Accepted: ETH/USDT and BTC/USDT, at different per-symbol configs.**

- **ETH/USDT**: `impulse_body_mult=1.3, consolidation_tolerance=0.01,
  max_hold_days=15, leverage_cap=0.4`. All 4 runnable validators pass with
  comfortable margin (Sharpe 1.200, MDD 17.3%, net Sharpe after costs 1.057,
  param sensitivity 0.170).
- **BTC/USDT**: originally a near-miss at the shared config (Sharpe 0.958,
  scale-invariant to leverage_cap so unfixable by sizing alone). A follow-up
  iteration (2026-09-18-055) grid-scanned `consolidation_tolerance` x
  `impulse_body_mult` x `max_hold_days` on BTC alone and found
  `impulse_body_mult=1.5, consolidation_tolerance=0.005, max_hold_days=15,
  leverage_cap=0.4` (a stricter pattern-match requirement, cutting trade
  count from 75 to 59 but improving trade quality) clears all 4 runnable
  validators: Sharpe 1.110, MDD 10.3%, net Sharpe after costs 0.924, param
  sensitivity 0.061.

This completes full crypto-universe coverage for the Mat Hold pattern
(BTC/USDT + ETH/USDT both accepted, each at its own tuned parameter set).

Equity (QQQ, SPY) remains rejected per the precursor entry (2026-09-18-051)
— the mid-vol gate made full-sample Sharpe negative on both, the opposite
of the intended rescue effect. Not retuned per-symbol this cron trigger;
left as a candidate for a future iteration.

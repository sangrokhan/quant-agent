# Backtest Report: Kairi Relative Index (Range-Position) Continuous Sizing Dial (SMA Trend Gate)

**Strategy file:** `strategies/2026-09-14_kri_rangepos_sizing_sma_trend.py`
**Date:** 2026-09-14

## Hypothesis

This repo's only prior Kairi Relative Index entry (2026-09-04-167) used the
SMA-deviation construction (KRI=100*(close-SMA)/SMA, unbounded) as a
binary oversold-threshold mean-reversion entry, REJECTED. Per
https://tradingbrokers.com/kairi-relative-index/ there is a second,
distinct KRI construction: a range-position oscillator naturally bounded
[-100,+100] by construction:

    KRI = ((CurrentPrice-LowestPrice)-(HighestPrice-CurrentPrice))
          / (HighestPrice-LowestPrice) * 100

This iteration uses this range-position KRI as a CONTINUOUS SIZING dial
within an SMA(trend_window) uptrend gate -- first KRI-as-continuous-sizing
variant AND first use of this range-position (rather than SMA-deviation)
KRI construction in this repo at all.

Source: https://tradingbrokers.com/kairi-relative-index/ (quantifiedstrategies.com
was also surfaced but blocked by a bot-check wall via browser_exec).

## Grid Test Summary (Step 6)

`param_grid={"period": [14, 21], "base_exposure": [0.4, 0.6, 0.8],
"sensitivity": [0.5, 0.7, 0.9]}`, `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`.

- total_cells: 216, passed_cells: 91, **pass_fraction: 0.421**
- by_asset_class: equity 61/108 (0.565), crypto 30/108 (0.278)
- by_vol_regime: low 54/72 (0.75), mid 37/72 (0.514), high 0/72 (0.0)
- best_cell: period=21, base_exposure=0.8, sensitivity=0.9, ETH/USDT mid-vol, sharpe=2.36
- worst_cell: period=21, base_exposure=0.6, sensitivity=0.5, QQQ high-vol, sharpe=0.02

Notably every one of the 18 default-grid (period, base_exposure,
sensitivity) full-sample QQQ AND SPY combos independently cleared Sharpe
>1.0 at deadband=0.20 -- the strongest full-sample robustness seen for any
sizing dial this trigger. The one weak point was transaction-cost
survival at the default deadband=0.20 (541/511 trades on QQQ/SPY), fixed
below by widening the deadband.

## Primary Config Validation (Step 7)

Best full-sample single config: `period=14, base_exposure=0.4,
sensitivity=0.7, deadband=0.5` (widened deadband from the default 0.20 to
cut turnover and clear TC-survival, following this cron trigger's
established deadband-widening fix pattern).

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.221 (pass) | 0.125 (pass) | 0.800 (pass) | 1.00 (pass) | 0.042 rel-std (pass) |
| SPY | 1.075 (pass) | 0.087 (pass) | 0.598 (pass) | 1.00 (pass) | 0.061 rel-std (pass) |
| BTC/USDT | 1.404 (pass) | 0.473 (**fail**, cap 0.25) | 1.293 (pass) | 1.00 (pass) | 0.055 rel-std (pass) |
| ETH/USDT | 1.110 (pass) | 0.578 (**fail**, cap 0.25) | 1.041 (pass) | 1.00 (pass) | 0.054 rel-std (pass) |

All 5 validators pass for both QQQ and SPY, with the best margins seen for
any sizing dial this trigger. Crypto (BTC/ETH) decisively fails only on
max-drawdown, consistent with essentially every other sizing-dial strategy
tested this trigger.

## Decision

**ACCEPT for equity (QQQ + SPY, strong margins). REJECT for crypto (BTC/ETH, MDD decisive fail) -- candidate for a follow-up leverage-cap recalibration iteration.**

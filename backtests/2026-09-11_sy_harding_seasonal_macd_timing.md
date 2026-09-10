# Backtest report: Sy Harding's Seasonal Timing Strategy (Best Six Months + MACD)

**Strategy file:** `strategies/2026-09-11_sy_harding_seasonal_macd_timing.py`
**Hypothesis source:** QuantifiedStrategies.com's "Sy Harding's Seasonal
Timing Strategy" (https://www.quantifiedstrategies.com/sy-hardings-seasonal-timing-strategy/,
visited this iteration via browser_exec fallback).

## Hypothesis

Sy Harding's enhancement of the Stock Trader's Almanac "Best Six Months"
calendar effect: instead of a fixed Oct 16/Apr 21 switch, use MACD (12,26,9)
crossovers near those anchor dates to fine-tune the exact entry/exit day.
Buy on/after Oct 16 when MACD line crosses above signal line (currently
flat); sell on/after Apr 21 when MACD line crosses below signal line
(currently long). Tested on QQQ/SPY (source's own portfolio backtest used a
diversified 5-asset-class portfolio including bonds/REITs/commodities, not
reproducible with this repo's single-symbol loaders, but the core MACD-
timed seasonal-switch mechanism is directly testable on any single equity
symbol).

The source's OWN disclosed full backtest (2007-2023, 5-asset diversified
portfolio) reported: CAR 0.86% vs buy-and-hold 4.57%, MDD -32.89% vs
buy-and-hold -47.77%, Sharpe -0.19 (worse than buy-and-hold's 0.10) -- i.e.
the source's own numbers already show this underperforms buy-and-hold on a
risk-adjusted basis, a candid red flag going into this iteration's test.

## Grid test summary (Step 6)

`param_grid={"anchor_lookforward_days": [10,20,40], "macd_fast": [12], "macd_slow": [26]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 36 total cells, 2015-01-01 to 2026-09-01.

- pass_fraction: 0.194 (7/36)
- by_asset_class: equity 7/18, crypto 0/18 (decisive -- crypto has no
  Northern-Hemisphere-institutional-flow seasonal analog, as expected)
- by_vol_regime: low 6/12, mid 1/12, high 0/12 -- edge concentrated almost
  entirely in the low-vol tercile.
- best_cell: QQQ, anchor_lookforward_days=20, low-vol regime, Sharpe=2.247
  -- a single vol-regime slice, not the full-sample result.

## Single-config validation (Step 7)

Full-sample (2015-01-01 to 2026-09-01) Sharpe / max drawdown:

| Symbol | anchor_lookforward_days | Sharpe | MDD |
|---|---|---|---|
| QQQ | 10 | 0.868 | 0.286 |
| QQQ | 20 | 0.779 | 0.286 |
| QQQ | 40 | 0.690 | 0.286 |
| SPY | 10 | 0.585 | 0.341 |
| SPY | 20 | 0.463 | 0.341 |
| SPY | 40 | 0.463 | 0.341 |

- `check_sharpe_ratio`: **FAILED** for both symbols across all
  `anchor_lookforward_days` values tested (best QQQ 0.868, best SPY 0.585,
  both < 1.0 threshold).
- `check_max_drawdown`: **FAILED decisively** for both (0.286 QQQ, 0.341
  SPY, both vs 0.25 budget) -- being long ~49% of calendar time with no
  intra-window trend/stop mechanism means the MACD-timed Nov-Apr window
  still holds through severe intra-window drawdowns (e.g. Feb-Mar 2020
  COVID crash falls within the "Best Six Months" window).
- Walk-forward / parameter-sensitivity: not run given the decisive
  full-sample Sharpe/MDD failure already confirmed across all 3
  `anchor_lookforward_days` values tested, consistent with the source's own
  disclosed underperformance-vs-buy-and-hold finding.

## Decision: REJECTED

Confirms the source's own candid finding: the MACD-timing refinement of
"Best Six Months" underperforms on a risk-adjusted basis on this repo's
single-symbol QQQ/SPY implementation, just as the source's own 5-asset
diversified-portfolio backtest reported a negative Sharpe. The MACD timing
trigger narrows the entry/exit window slightly (compressing exposure from a
fixed 6-month calendar block to whenever MACD first confirms near the
anchor dates) but does not address the fundamental drawdown-during-the-
long-window risk that the underlying pure-calendar Sell-in-May/Halloween
strategies already failed on in this repo (2026-09-09-019/020).

## Notes for future loops

- This adds a third data point (after 2026-09-09-019 pure calendar and
  2026-09-09-020 calendar+trend+vol-gate) to this repo's consistent finding
  that the "Best Six Months"/Sell-in-May family does not clear this repo's
  validator bar on QQQ/SPY in any variant tried so far (pure calendar,
  trend+vol-gated, or MACD-timed) -- treat this family as thoroughly
  exhausted rather than a candidate for further fine-tuning.

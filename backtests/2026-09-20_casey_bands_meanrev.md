# Backtest Report: Casey Bands Mean Reversion

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_casey_bands_meanrev.py`
**Source:** https://statoasis.com/overfit/research/how-to-build-a-profitable-strategy-using-casey-bands-(free-code-included) (Ali Casey / StatOasis, visited via `browser_exec`)

## Hypothesis

Casey Bands anchor the upper band to a smoothed EMA of the highs and the
lower band to a smoothed EMA of the lows (rather than Bollinger's
close-based SMA or Keltner's close-based EMA), so the channel reflects
where price actually reached. Close% (PercentC) crossing below an entry
threshold marks oversold-relative-to-range-extremes conditions worth a
mean-reversion long.

## Grid Test Summary (Step 6)

`param_grid={"entry_level": [10,20,30], "atr_mult": [1.0,1.25,1.75]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2018-01-01 to 2026-09-01.

- **Total cells:** 108, **passed:** 9, **pass_fraction:** 0.083 (weak)
- **By asset class:** equity 9/54 (0.167), crypto 0/54 (0.0)
- **By vol regime:** low 9/36 (0.25), mid/high 0/36 each
- **Best cell:** equity/SPY, low-vol, `entry_level=20, atr_mult=1.25`,
  Sharpe 1.76
- Best full-sample-averaged config: `atr_mult=1.75, entry_level=30.0`
  (avg equity Sharpe 0.631)

Weak grid overall -- crypto never passes a single cell, and even equity's
pass fraction (0.167) is well below what this repo's accepted strategies
typically show.

## Single-Config Validation (Step 7) — `atr_mult=1.75, entry_level=30.0`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd (4-split) | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.425 (FAIL) | 0.406 (FAIL) | 0.376 (FAIL) | 0.75 (PASS) | 0.290 (PASS) |
| SPY | 0.675 (FAIL) | 0.256 (FAIL) | 0.607 (PASS) | 1.00 (PASS) | 0.286 (PASS) |

## Decision (Step 8): **REJECTED**

Decisive rejection: fails Sharpe on both symbols (0.43-0.68 vs 1.0
threshold) and fails max-drawdown on both (0.41 on QQQ, 0.26 on SPY vs
0.25 threshold). Crypto never passed a single grid cell. This repo's own
adaptation (long-only, generic entry/exit-level cross rather than the
source's own sweep-optimized 116,640-variant "most durable setting", which
included short variants and a broader parameter search this single
iteration's modest grid didn't replicate) evidently falls well short of
the source's own reported result -- the source's headline finding (Casey
Bands beat buy-and-hold on MAR after costs) was for a specific
sweep-selected configuration this iteration's coarser grid did not locate,
if it exists within the ranges tested. Not a near-miss; a clean reject at
the config found here.

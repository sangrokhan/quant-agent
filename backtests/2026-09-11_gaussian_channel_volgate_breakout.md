# Gaussian Channel breakout + low-vol-regime gate — REJECTED

**Iteration ID:** 2026-09-11-011
**Date:** 2026-09-11

## Hypothesis

Direct fix attempt for previously-rejected `2026-09-06-180` (plain Gaussian
Channel breakout). That entry's own `notes` field explicitly suggested
adding a low-vol-regime gate given its edge was concentrated in low/mid-vol
equity grid cells (low 12/24 pass, mid 6/24, high 0/24). This iteration
reused the accepted `strategies/2026-09-03_bb_meanrev_qqq_volregime.py`
low-vol-regime construction (20d realized vol <= trailing 252d median) as
an explicit AND-gate on top of unchanged Gaussian Channel breakout entry/exit
mechanics (upper-band cross + rising channel + 200d SMA bull filter).

Sources: https://kr.tradingview.com/scripts/gaussianchannel (Gaussian
Channel construction), TRADLEWARE "Gaussian Channel + Stochastic RSI"
TradingView writeup (cited in 2026-09-06-180), and
https://www.tradingview.com/script/xTnfnVLA-SM-021-Gaussian-Trend-System-Optimized/
(confluence-filter pattern that motivated this iteration's search).

## Step 6 grid summary

Grid: `sampling_period=[89,144] x tr_mult=[1.0,1.414,2.0] x vol_regime_ratio=[1.0,1.2]`,
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), `vol_regime_splits=3`,
2015-01-01 to 2026-09-01, 144 total cells.

- **pass_fraction: 0.0139 (2/144)** — vs the ungated predecessor's 0.25 (18/72)
- by_asset_class: equity 2/72 (2.8%), crypto 0/72 (0%)
- by_vol_regime: low 2/48 (4.2%), mid 0/48, high 0/48
- best_cell: QQQ low-vol, `sampling_period=89, tr_mult=2.0, vol_regime_ratio=1.0`, Sharpe=1.265 (single grid cell, not full-sample)

## Step 7 single-config validation (best config: sampling_period=89, tr_mult=2.0, vol_regime_ratio=1.0, trend_window=200, max_hold_days=30)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full-sample) | 0.498 | 0.465 | 1.0 | FAIL both |
| Max Drawdown | 0.026 | 0.024 | 0.25 | PASS both (trivially, near-zero exposure) |
| Transaction cost survival (net Sharpe) | 0.488 | 0.430 | 0.5 | FAIL both |
| Num trades (full sample, 2015-2026) | 1 | 3 | — | — |
| Walk-forward | not run | not run | — | skipped: decisive rejection already established |
| Parameter sensitivity | not run separately | — | — | grid pass_fraction (0.0139) itself demonstrates extreme sensitivity/fragility |

## Decision: REJECTED

Adding the low-vol-regime gate on top of the already-restrictive
breakout + rising-channel + 200-SMA-trend filter stack made entries
extremely rare (QQQ 1 trade, SPY 3 trades over 11.5 years). Both symbols
fail full-sample Sharpe and transaction-cost survival despite trivially
passing max drawdown (near-zero market exposure isn't a real edge). Crypto
rejected decisively (0/72 grid cells), consistent with the ungated
predecessor.

## Lesson for future loops

The established "add a low-vol-regime gate" fix pattern (successful for BB
mean-reversion `2026-09-03-001`) does **not** generalize to every rejected
breakout strategy. When the base strategy already stacks multiple
restrictive AND-gates (breakout + channel-color + long-SMA-trend), adding
one more regime filter can over-restrict entries into statistical
insignificance rather than concentrating the edge. A future revisit of
Gaussian Channel should try **relaxing** a filter (e.g. drop the 200-SMA
gate, or widen `tr_mult`) rather than adding another one.

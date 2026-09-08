# Backtest Report: Conditional Reversal-Tilted Momentum (B = (1+r)*M, single-asset TSMOM analog)

**Date:** 2026-09-08
**Strategy file:** `strategies/2026-09-08_conditional_reversal_tilt_momentum.py`
**Source:** Quantitativo Weekly #2, https://www.quantitativo.com/p/quantitativo-weekly-4f8
(summarizing "Winners Glide, Losers Stumble: A Behavioral Reversal Tilt to
Momentum", read via browser_exec fallback after web_extract failed with
"DuckDuckGo is a search-only backend" error).

## Hypothesis

The source paper's zero-parameter identity B = (1+r)*M (r = last-month gross
return, M = 12-1 momentum) improves cross-sectional stock momentum's worst
crash months by de-weighting rebounded losers harder than still-falling
ones. Adapted here as a single-asset time-series signal: long when the
asset's own B score is positive, using its own 12-1 momentum and its own
last-month return (no cross-sectional ranking available in this repo's
single-symbol backtests).

## Grid test summary (Step 6)

`param_grid={"lookback_days":[126,252], "skip_days":[10,21], "b_threshold":[0.0,0.02]}`,
`symbols={"equity":["QQQ","SPY"], "crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **total_cells:** 96, **passed:** 22, **pass_fraction: 0.229**
- **by_asset_class:** equity 22/48; crypto 0/48 (decisive reject)
- **by_vol_regime:** low 16/32, mid 6/32, high 0/32 (edge concentrates
  entirely in low-vol regime, zero survival in high-vol)
- **best_cell:** SPY, lookback_days=252, skip_days=10, b_threshold=0.0,
  low-vol regime, Sharpe 2.66

## Single-config validation (Step 7): lookback_days=252, skip_days=10, b_threshold=0.0

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.996 (**FAIL**, borderline) | 0.588 (**FAIL**) | >= 1.0 |
| Max drawdown | 0.286 (**FAIL**) | 0.343 (**FAIL**) | <= 0.25 |
| TC survival (5bps/trade, 23 trades) | 0.986 (PASS) | 0.576 (PASS) | >= 0.5 |
| Walk-forward (4 manual chunks) | 0.75 (PASS, borderline) | 0.5 (**FAIL**) | >= 0.75 |
| Parameter sensitivity (relative_std, 8-combo grid) | 0.136 (PASS) | 0.176 (PASS) | <= 0.5 |

(Manual 4-chunk walk-forward workaround used per pre-existing
`vbt.utils.splitting` AttributeError bug, documented since 2026-09-03.)

## Decision: REJECT

Full-sample Sharpe misses the 1.0 bar on both equities (0.996 QQQ borderline,
0.588 SPY decisively), and MDD fails both (0.286/0.343 vs 0.25). Only the
low-vol grid slice performs well (best cell Sharpe 2.66) — the strategy's
full-sample average is dragged down heavily by mid/high-vol-regime failure
(0/32 high-vol cells passed), consistent with a long-only absolute-momentum
signal that has no defense once a regime turns choppy/volatile. The
skip-days=10 config (best in the grid) differs from the more standard
21-day skip-month convention and only barely improves matters. Crypto
rejected decisively (0/48). The reversal-tilt mechanism itself (multiplying
by (1+r)) did not materially fix the underlying long-only-momentum
weaknesses already seen in this repo's other momentum variants (e.g.
2026-09-03-012 plain 12-month TSMOM, also rejected) when applied
time-series/single-asset rather than cross-sectionally, which is the
paper's actual tested design — this single-asset adaptation likely loses
most of the paper's edge, which fundamentally comes from RANKING many
stocks' B scores against each other, not from an absolute threshold on one
asset's own B score. Not worth revisiting without a genuine
cross-sectional stock universe, which this repo's single-symbol
architecture doesn't support.

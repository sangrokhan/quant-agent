# Williams %R Continuous Inverse-Sizing Overlay on SMA(200) Trend Gate

**Hypothesis:** Williams %R (Larry Williams) = (HighestHigh(window) -
Close) / (HighestHigh(window) - LowestLow(window)) * -100, bounded
[-100, 0]. This repo has 6+ prior Williams %R entries, all binary
threshold entries. This iteration reuses the "bounded oscillator as
continuous sizing dial" pattern from this cron trigger's two other
accepted strategies (Bollinger %B 2026-09-13-071, Aroon Oscillator
2026-09-13-072) on a third distinct bounded-oscillator family: exposure =
clip(base_exposure - wr_sensitivity*(williams_r/100.0), 0, leverage_cap) --
reduce exposure as price approaches the recent high (%R toward 0),
increase exposure as price pulls back toward the recent low (%R toward
-100) within the broader SMA(200) uptrend. First Williams-%R-as-continuous-
sizing strategy in this repo.

**Source:** Williams %R formula (Larry Williams, well-established from 6+
prior repo entries; standard formula, no new fetch needed this iteration).

## Grid test summary (equity: SPY/QQQ, crypto: BTC/USDT/ETH/USDT;
williams_window in [10,14,20], base_exposure in [0.7,0.9,1.0];
vol_regime_splits=3)

- total_cells: 108, passed_cells: 27, pass_fraction: 0.25
- by_asset_class: equity 27/54 passed, crypto 0/54 passed
- by_vol_regime: low 18/36, mid 9/36, high 0/36
- best_cell: SPY, williams_window=20, base_exposure=0.7, low-vol, Sharpe=2.902
- worst_cell: ETH/USDT, williams_window=20, base_exposure=0.7, mid-vol, Sharpe=0.034

## Single-config validator results (best full-sample config per symbol:
williams_window=10, base_exposure=1.0, wr_sensitivity=0.6, trend_window=200)

| Symbol | Sharpe | Passed | MDD | Passed | Net Sharpe (5bps/trade) | Passed | Walk-fwd frac | Passed | Param sens (rel std) | Passed |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | 0.990 | No (thr 1.0) | 0.208 | Yes | 0.957 | Yes | 0.75 | Yes | 0.008 | Yes |
| QQQ | 1.253 | Yes | 0.219 | Yes | 1.241 | Yes | 0.75 | Yes | 0.010 | Yes |

Note: `validators.check_walk_forward` has the same pre-existing tooling gap
(`vbt.utils.splitting.RangeSplitter` unavailable) — substituted a manual
4-split walk-forward (same 0.75 threshold); both symbols hit 3/4.

## Decision

**Accepted (QQQ only).** All 5 validators pass for QQQ. SPY fails only the
Sharpe threshold (0.990 < 1.0, a narrow near-miss by 0.010) with every
other validator passing (including an extremely tight parameter
sensitivity, 0.008 -- though this may indicate the sizing signal has
limited genuine variation across the swept range, similar to the
degeneracy noted in this cron trigger's Downside-Beta SPY entry). Crypto
(BTC/USDT, ETH/USDT) rejected decisively across the whole grid (0/54
cells).

## Cron-trigger-wide observation

This trigger tested THREE bounded-oscillator-as-continuous-sizing
strategies back to back: Bollinger %B (accepted QQQ), Aroon Oscillator
(accepted QQQ, best result of the three at Sharpe 1.412), and Williams %R
(accepted QQQ). All three share the same qualitative outcome: QQQ accepted,
SPY a narrow Sharpe near-miss, crypto decisively rejected. This is a
useful confirmed pattern for future iterations: bounded price-position/
recency oscillators reused as continuous sizing dials on the SMA(200)
trend gate reliably clear the bar for QQQ but not quite for SPY in this
repo's data window, unlike this cron trigger's earlier risk-ratio-based
overlays (Coefficient of Variation, SQN, Downside Beta) which showed more
mixed QQQ/SPY split patterns.

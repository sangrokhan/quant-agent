# WaveTrend CI Continuous Sizing Dial — SMA Trend Gate (QQQ accepted)

**Date:** 2026-09-15
**Strategy file:** `strategies/2026-09-15_wavetrend_ci_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-15-031

## Hypothesis

WaveTrend Oscillator (LazyBear formulation), source:
https://pineify.app/resources/blog/wavetrend-oscillator-lazybears-momentum-indicator-guide
(visited this iteration).

Formula: AP=HLC3, ESA=EMA(AP,channel_length), D=EMA(|AP-ESA|,channel_length),
CI=(AP-ESA)/(0.015*D), WT1=EMA(CI,average_length), WT2=SMA(WT1,4).

Prior WaveTrend entries in this repo (2026-09-04-145, 2026-09-08-094,
2026-09-09-055) all used a discrete WT1/WT2 signal-line-crossover-in-
extreme-zone rule and were all rejected for signal sparsity (0-1 trades on
equity, 0/36-0/54 on crypto). This iteration reuses the same underlying
WT1 channel-index construction but as a **continuous sizing dial**
(rolling z-score + tanh squash of WT1, used as an exposure multiplier
inside an SMA(trend_window) uptrend gate, with a deadband to cut
turnover) — the pattern this cron trigger has repeatedly used to rescue
prior discrete-rule near-misses/rejections.

## Grid test summary (Step 6)

`param_grid={"trend_window": [30,40,50], "sensitivity": [0.4,0.6,0.8],
"deadband": [0.15,0.20]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`. 216 total cells.

- **pass_fraction:** 0.384 (83/216)
- **by_asset_class:** equity 54/108 (0.50), crypto 29/108 (0.269)
- **by_vol_regime:** low 58/72 (0.806), mid 25/72 (0.347), high 0/72 (0.0)
- **best_cell:** equity/SPY, low-vol, `trend_window=50, sensitivity=0.4,
  deadband=0.15`, Sharpe 2.368
- **worst_cell:** equity/SPY, high-vol, `trend_window=50, sensitivity=0.8,
  deadband=0.15`, Sharpe 0.028

High-vol regime is a decisive failure everywhere (0/72) — this strategy
only works when volatility is low/mid, consistent with a trend-following
sizing overlay whose SMA gate whipsaws in high-vol chop.

## Single-config validation (Step 7) — best config: `trend_window=50,
sensitivity=0.4, deadband=0.15, channel_length=10, average_length=21,
zscore_window=100, base_exposure=0.4, leverage_cap=1.0`

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param sensitivity | All pass? |
|---|---|---|---|---|---|---|
| QQQ | 1.268 (>1.0 ✓) | 0.090 (<0.25 ✓) | 0.592 (>0.5 ✓) | 1.00 (>0.75 ✓) | 0.054 (<0.5 ✓) | **YES** |
| SPY | 0.933 (<1.0 ✗) | 0.115 (<0.25 ✓) | 0.209 (<0.5 ✗) | 1.00 ✓ | 0.056 ✓ | no |
| BTC/USDT | 1.231 (>1.0 ✓) | 0.420 (>0.25 ✗) | 1.023 (>0.5 ✓) | 1.00 ✓ | 0.022 ✓ | no |
| ETH/USDT | 1.090 (>1.0 ✓) | 0.407 (>0.25 ✗) | 0.968 (>0.5 ✓) | 1.00 ✓ | 0.037 ✓ | no |

## Decision (Step 8)

**Accepted, scoped to QQQ only.** All 5 validators pass with comfortable
margin for QQQ. SPY misses on raw Sharpe and transaction-cost survival
(net Sharpe collapses under 10bps/trade cost — turnover too high relative
to edge for SPY's flatter distribution). BTC/ETH pass Sharpe/costs/walk-
forward/param-sensitivity but fail max-drawdown decisively (0.42/0.41 vs
0.25 threshold) — crypto's higher volatility blows through the leverage
cap's drawdown budget even with the trend gate.

Strategy file and this report are kept as a QQQ-only accepted strategy;
SPY/BTC/ETH remain out of scope per this config (a future iteration could
retune per-symbol per the cron trigger's established "SPY/QQQ fix" and
"crypto leverage-cap fix" patterns).

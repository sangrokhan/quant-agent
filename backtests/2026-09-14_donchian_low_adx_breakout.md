# Backtest Report: Donchian Breakout Gated by LOW ADX (Consolidation-Before-Breakout)

**Strategy file:** `strategies/2026-09-14_donchian_low_adx_breakout.py`
**Knowledge base id:** 2026-09-14-116

## Hypothesis

Source: https://www.quantifiedstrategies.com/how-we-built-bitcoin-trend-following-strategy/
A Donchian breakout gated by ADX(14) BEING BELOW a threshold (25) at the
time just before the breakout, rather than above it (this repo's usual
"high ADX confirms an established trend" gate, tested 34 times across
other indicator pairings, e.g. 2026-09-03-017, 2026-09-04-162,
2026-09-06-098). The article's rationale: assets like Bitcoin coil in a
low-volatility/low-ADX consolidation immediately before an explosive
breakout, so a LOW-ADX pre-condition selects for "quiet before the storm"
setups rather than confirming a trend already partway through. Exit uses
this repo's established Chandelier-Exit-style monotonically-ratcheting ATR
trailing stop (not the article's simple fixed N-day-low exit).

## Config tested (per-symbol full-sample best config)

- QQQ: donchian_window=25, adx_max=30.0, atr_multiplier=3.0
- SPY: donchian_window=40, adx_max=25.0, atr_multiplier=3.0
- BTC/USDT: donchian_window=15, adx_max=25.0, atr_multiplier=3.0

## Single-config validator results

| Validator | QQQ | SPY | BTC/USDT |
|---|---|---|---|
| Sharpe (>=1.0) | 1.282 PASS | 0.464 FAIL | 0.233 FAIL |
| Max Drawdown (<=0.25) | 0.158 PASS | 0.246 PASS (narrow) | 0.566 FAIL |
| TC survival (10bps/trade, net Sharpe >=0.5) | 1.199 PASS (53 trades) | 0.350 FAIL (57 trades) | 0.075 FAIL (1535 trades) |
| Walk-forward (4 manual contiguous folds, >=0.75) | 1.0 PASS (4/4) | 0.75 PASS (3/4) | 1.0 PASS (4/4) |
| Param sensitivity (donchian_window x adx_max x atr_multiplier sweep, rel-std <=0.5) | 0.144 PASS | 0.170 PASS | 0.138 PASS (base already failing) |
| **All pass?** | **YES** | **NO (Sharpe/TC fail)** | **NO (Sharpe/MDD/TC all fail)** |

Note: manual contiguous 4-fold walk-forward substitute used (vectorbt
1.1.0's `RangeSplitter` unavailable, consistent with prior iterations'
documented workaround).

## Grid summary (Step 6)

`param_grid={donchian_window: [15,25,40], adx_max: [20,25,30],
atr_multiplier: [2.5,3.0]}`, `symbols={equity:[QQQ,SPY],
crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`.

- total_cells=216, passed_cells=53, **pass_fraction=0.245**
- by_asset_class: equity 53/108 passed, **crypto 0/108 passed**
- by_vol_regime: low 36/72, mid 17/72, **high 0/72**
- best_cell: QQQ, donchian_window=25, adx_max=30.0, atr_multiplier=3.0,
  low-vol regime, Sharpe=2.600

## Decision: ACCEPT (QQQ only) / REJECT (SPY near-miss) / REJECT (crypto)

QQQ passes all 5 validators cleanly (Sharpe 1.282, MDD 15.8%, TC-survival
net Sharpe 1.199 on only 53 trades over the sample, WF 4/4, param
sensitivity rel-std 0.144). SPY is a genuine near-miss: MDD narrowly passes
(24.6% vs 25% threshold) but full-sample Sharpe (0.464) and TC-survival
(0.350) fail decisively -- the low-ADX pre-breakout filter appears to
select fewer/lower-quality setups on SPY than on QQQ at any config tried in
this grid. Crypto (BTC/USDT) fails decisively on all three headline
validators, and notably generated 1535 trades over the sample (vs
QQQ's 53) -- the LOW-ADX gate does not meaningfully suppress crypto's
constant high-frequency chop the way it does for equities, so the strategy
ends up re-entering and getting stopped out repeatedly rather than finding
genuine "quiet before the storm" setups.

**This is yet another mechanism (ADX used as a LOW-threshold pre-condition
gate rather than a directional-sizing dial or breakout-ensemble) that fails
crypto decisively, this time driven by trade-count/turnover explosion
rather than pure drawdown magnitude -- reinforcing the repo's accumulating
evidence that crypto's regime structure (near-constant elevated ADX/no
extended quiet consolidations the way equities have) may make many
equity-tuned trend-following gate designs structurally mismatched for
crypto specifically, independent of the underlying indicator or ensemble
technique chosen.**

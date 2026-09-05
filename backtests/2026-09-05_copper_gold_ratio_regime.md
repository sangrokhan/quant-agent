# Copper/Gold Ratio Z-Score Regime Filter — Backtest Report

**Hypothesis:** HG=F/GC=F (copper futures / gold futures) price ratio
rolling z-score signals a cyclical growth vs safe-haven macro regime; long
(risk-on) when z-score rises above threshold (copper strong = industrial
demand/growth), flat (risk-off) when z-score falls below threshold (copper
weak vs gold = economic slack), holding prior state in between.

**Source:** https://www.quantifiedstrategies.com/copper-gold-ratio-trading-strategy/
-- source's own backtest is a contrarian commodities-timing rule (ratio <
0.19 for the first time in a year -> buy copper AND gold, strong 1-12mo
forward returns), not an equity regime filter. This backtest adapts the
same "cyclical growth vs safe-haven" rationale to an equity/crypto
long/flat gate using the adaptive z-score mechanism validated for
gold/silver (2026-09-05-030, accepted).

**Strategy file:** `strategies/2026-09-05_copper_gold_ratio_regime.py`

## Step 6 — Grid test summary (param_grid: low_z_threshold in
[-1.5,-1.0,-0.5] x high_z_threshold in [0.0,0.5,1.0] x ratio_lookback in
[126,252]; symbols: equity QQQ/SPY, crypto BTC/USDT, ETH/USDT;
vol_regime_splits=3; period 2019-01-01..2026-09-01)

- total_cells: 216, passed_cells: 45, **pass_fraction: 0.208**
- by_asset_class: equity 45/108 (42%), crypto 0/108 (0%) -- again zero
  transfer to crypto.
- by_vol_regime: low 36/72, mid 5/72, high 4/72 -- mostly a low-vol-only
  effect here (unlike gold/silver ratio 2026-09-05-030, which passed in
  both low and high vol regimes).
- best_cell: low_z_threshold=-0.5, high_z_threshold=1.0,
  ratio_lookback=126, QQQ, low-vol regime, Sharpe=2.55 (tercile slice, not
  full period).

## Step 7 — Single-config validators (best grid config over FULL period:
low_z_threshold=-0.5, high_z_threshold=1.0, ratio_lookback=126)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.961 (near-miss) | PASS 1.038 |
| Max Drawdown (<= 0.25) | PASS 0.191 | PASS 0.127 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 26 trades) | PASS 0.921 | PASS 0.979 |
| Parameter sensitivity (relative_std <= 0.5, 9-cell QQQ sweep) | PASS 0.216 | n/a |

Walk-forward not run (pre-existing `vbt.utils.splitting` AttributeError bug
in this repo's installed vectorbt version, consistent with other entries).

## Outcome: **REJECTED (QQQ Sharpe near-miss); SPY alone would have passed**

QQQ Sharpe fails narrowly (0.961 vs 1.0 threshold) at the best grid config,
while SPY clears every validator. Since the primary evaluated config is
shared across both symbols and one fails, this is judged an overall reject
-- but it's a genuine near-miss worth revisiting: MDD, transaction cost
survival, and parameter sensitivity all comfortably pass on both symbols,
and the only failure is a single Sharpe reading 4% below threshold. A
future iteration could retest with a slightly wider ratio_lookback or a
looser high_z_threshold (grid showed some higher-Sharpe cells) or restrict
scope to SPY-only if QQQ specifically remains a laggard. Crypto again shows
zero transfer (0/108). Distinct from gold/silver ratio (2026-09-05-030,
accepted) which passed cleanly on both QQQ and SPY at its best config and
uniquely worked across both low AND high vol regimes -- copper/gold here
is low-vol-regime-dependent like most other macro filters in this repo.

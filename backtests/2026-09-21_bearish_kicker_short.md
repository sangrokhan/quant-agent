# Bearish Kicker Short — Backtest Report (2026-09-21)

## Hypothesis
Source: https://www.quantifiedstrategies.com/bearish-kicker-candlestick-pattern/
(read via browser_exec fallback). 2-candle bearish reversal at the top of
an uptrend: candle 1 = long bullish candle; candle 2 = bearish candle that
opens above candle 1's high (gap-up "exhaustion gap") and closes at or
below candle 1's midpoint. Source recommends short/short-put on
confirmation, but discloses no specific numeric stop/target -- only
generic risk-management guidance, and explicitly reports only a 47%
success rate in its own candlestick study (a stated low prior for this
pattern). Exit rules here are this repo's standard ATR stop/target
construction, not source-disclosed.

Strategy file: `strategies/2026-09-21_bearish_kicker_short.py`

## Step 6 — Grid test summary
`grid_summary_bearish_kicker_short.json` /
`grid_cells_bearish_kicker_short.json`

- Grid: `trend_window` in {30, 50}, `tall_body_min_pct` in {0.4, 0.5, 0.6},
  `target_atr_mult` in {1.5, 2.0, 3.0}; symbols QQQ/SPY (equity), BTC/USDT,
  ETH/USDT (crypto); vol_regime_splits=3; 216 total cells.
- **pass_fraction: 0.009** (2/216 cells). Both passing cells: QQQ,
  high-vol-regime, `trend_window=50, target_atr_mult=2.0`,
  Sharpe=1.0055 (razor-thin), MDD=0.057.
- by_asset_class: equity 2/108, crypto 0/108. by_vol_regime: low 0/72,
  mid 0/72, high 2/72.

## Step 7 — Single-config validation (QQQ, best-cell params, full sample
2018-2026, no vol-regime gate)

Params: `trend_window=50, tall_body_min_pct=0.4, target_atr_mult=2.0`.

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | **False** | -0.0007 | >= 1.0 |
| max_drawdown | True | 0.067 | <= 0.25 |
| transaction_cost_survival | **False** | -0.130 net Sharpe (10bps/trade, 38 trades) | >= 0.5 |
| walk_forward (4 splits) | **False** | 0.5 pass fraction ([F,T,T,F]) | >= 0.75 |
| parameter_sensitivity | **False** | rel_std 0.781 | <= 0.5 |

38 position changes (19 round-trips) over the full 2018-2026 QQQ sample --
enough trades for a meaningful sample, and the full-sample Sharpe is
essentially flat (-0.0007), consistent with the source's own disclosed 47%
success-rate finding. The single passing grid cell (high-vol-tercile
subset) was a small-sample artifact, not a real edge: once tested on the
full sample it fails Sharpe, transaction-cost survival, walk-forward, and
parameter sensitivity.

## Step 8 — Decision: **REJECT**

Rejection reason: fails Sharpe, transaction-cost survival, walk-forward,
and parameter sensitivity on full-period single-config validation. Grid
pass_fraction 0.9% (2/216), entirely confined to one high-vol-regime QQQ
slice that doesn't replicate out-of-slice. Consistent with the source's
own disclosed low (47%) success-rate prior for this pattern.

Strategy file and this report are kept as a record of a rejected attempt.

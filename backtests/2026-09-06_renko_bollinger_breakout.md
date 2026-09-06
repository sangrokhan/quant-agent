# Renko chart Bollinger Band breakout (long-only)

## Hypothesis
FXOpen's "Renko With Bollinger Bands Strategy": reconstruct an ATR-sized
Renko brick series from daily closes; compute Bollinger Bands (bb_window=20,
bb_std=1.5 -- source: "adjusting Bollinger Bands to 1.5 standard deviations
in this strategy sharpens the focus on volatility shifts") on the brick
closes; long entry when `confirm_bricks` (2-3) consecutive up-bricks close
above the upper Bollinger Band ("observing two (or three for a more
conservative approach) consecutive Renko brick closes outside the Bollinger
Bands"); exit on the first down-brick ("take profit after one or two bricks
of the opposite colour appear") or a max_hold_days time-stop.

Source: https://fxopen.com/blog/en/renko-trading-strategies-how-to-trade-with-renko-charts/
("Renko With Bollinger Bands Strategy" section, read in-browser).

First Renko+Bollinger-Band strategy in this repo -- distinct from prior
Renko strategies (2026-09-04-086 pure brick-count trend-follow,
2026-09-04-087 its ADX-gated fix, both rejected) since this adds a
volatility-band breakout confirmation rather than a pure brick-count rule.

## Grid test (Step 6)
`param_grid={"brick_atr_mult": [0.5,1.0,1.5], "confirm_bricks": [2,3]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`. 2019-01-01 to 2026-09-01.

- total_cells: 72, passed: 8, **pass_fraction: 0.111**
- by_asset_class: equity 8/36, **crypto 0/36**
- by_vol_regime: low 7/24, mid 1/24, high 0/24 (only works in calm markets)
- best_cell: brick_atr_mult=1.5, confirm_bricks=2, QQQ, low-vol, Sharpe 1.61
- Best avg-across-regimes config: brick_atr_mult=1.5, confirm_bricks=2/3
  (QQQ avg Sharpe ~0.98, still short of the 1.0 full-sample bar); SPY avg
  Sharpe only 0.41 at the same config -- doesn't generalize across even the
  two equity tickers.

## Single-config validation (brick_atr_mult=1.5, confirm_bricks=2, QQQ, full sample)
| Validator | Result | Evidence |
|---|---|---|
| Sharpe ratio (>=1.0) | **FAIL** | 0.880 |
| Max drawdown (<=25%) | PASS | 13.9% |
| Transaction cost survival | PASS | net Sharpe 0.770, 62 trades |

## Decision: REJECT
Decisive: only 11.1% grid pass fraction, entirely confined to equity
low-vol cells, crypto 0/36 outright, and even the single best-scoring
config fails the primary Sharpe threshold on the full QQQ sample (0.88 vs
1.0). No further validators run given the Sharpe failure at the best
config makes the strategy a clear reject per Step 8.

## Notes
- Strategy file kept in `strategies/` as a rejected-attempt record.

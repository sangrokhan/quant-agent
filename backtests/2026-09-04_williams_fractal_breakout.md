# Backtest Report: Bill Williams Fractal Breakout with Trailing Fractal Stop

**Strategy file:** `strategies/2026-09-04_williams_fractal_breakout.py`
**Hypothesis id:** 2026-09-04-134
**Source:** https://theindicatorlab.com/reviews/fractals-bill-williams/

## Hypothesis

Bill Williams Fractals (5-bar swing patterns, default left/right=2 bars):
a fractal high is a bar whose high exceeds `left_bars` bars before and
`right_bars` bars after it; a fractal low is the mirror. Per the source's
own systematic entry rule, after a fractal low forms, a later close
breaking above the most recently confirmed fractal high is the long
entry (pullback-reversal-continuation in a trend). The mirrored exit is a
trailing stop at the most recently confirmed fractal low: exit when close
breaks below it. Both fractal levels are only knowable `right_bars` bars
after formation (shifted forward to avoid look-ahead). A `max_hold_days`
time-stop backstop was added since the source's pure mirror-fractal exit
can theoretically hold indefinitely.

## Single-config validators (QQQ, left_bars=3, right_bars=2, max_hold_days=30)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| sharpe_ratio | ✅ | 1.178 | ≥ 1.0 |
| max_drawdown | ❌ | 0.268 | ≤ 0.25 |
| transaction_cost_survival (10bps/trade, 50 trades) | ✅ | net Sharpe 1.109 | ≥ 0.5 |
| walk_forward (manual 4-equal-slice fallback; `vbt.utils.splitting.RangeSplitter` still broken in this install) | ✅ | 4/4 splits positive Sharpe | ≥ 0.75 pass fraction |
| parameter_sensitivity | ✅ | relative std 0.051 (8-combo grid) | ≤ 0.5 |

## Step 6 grid summary

`param_grid={left_bars:[2,3], right_bars:[2,3], max_hold_days:[30,60]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
96 cells total.

- **pass_fraction:** 0.260 (25/96)
- **by_asset_class:** equity 25/48 passed (52%); crypto 0/48 passed (0%)
- **by_vol_regime:** low 16/32; mid 8/32; high 1/32
- **best_cell:** left_bars=3, right_bars=2, max_hold_days=30, QQQ, low-vol regime, Sharpe 3.43
- **worst_cell:** left_bars=3, right_bars=3, max_hold_days=60, QQQ, high-vol regime, Sharpe -0.50

## Decision: REJECT

Max drawdown (0.268) narrowly exceeds the 0.25 threshold -- a near-miss,
not a decisive failure (everything else passes cleanly, including
walk-forward and parameter sensitivity, which are usually the harder
bars to clear). The grid also shows the edge is equity-only and
concentrated in low/mid volatility regimes (crypto is a hard 0/48, and
high-vol equity cells mostly fail too), consistent with the source's own
caveat that fractals are dangerous outside trending conditions. Worth
revisiting with an explicit MDD-reduction lever (e.g. tighter ATR-based
stop instead of relying solely on the trailing fractal, or a vol-regime
gate that only trades in low/mid-vol equity conditions where the grid
already shows the edge concentrates).

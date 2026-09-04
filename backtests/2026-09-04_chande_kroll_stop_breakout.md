# Chande Kroll Stop (CKS) Breakout — Backtest Report (2026-09-04)

## Hypothesis
Chande Kroll Stop (Tushar Chande & Stanley Kroll, 1994): an ATR-based pair
of trailing stop/breakout lines. Initial high stop = Highest(high,p) -
atr_mult*ATR(p); Initial low stop = Lowest(low,p) + atr_mult*ATR(p); Short
stop = Highest(initial high stop, q); Long stop = Lowest(initial low stop,
q). Source states a buy signal fires when price crosses above BOTH stop
lines. Implemented long-only: enter on close crossing above short_stop,
exit on close crossing below long_stop or a max_hold_days time-stop.

Sources:
- https://www.quantifiedstrategies.com/chande-kroll-stop/ (web_search
  worked for this query; overview + general finding that adding the stop
  underperforms a no-stop baseline on SMH; full coded rules gated)
- https://trendspider.com/learning-center/chande-kroll-stop-a-comprehensive-guide/
  (web_extract failed -- ddgs backend cannot extract -- fell back to
  browser_exec reading rendered DOM text; gives the exact formula and the
  explicit "buy when price crosses above both lines" breakout rule used
  here)

## Grid summary (Step 6)
`param_grid={p:[10,20], atr_mult:[1.0,2.0,3.0]}` (q=9, max_hold_days=20
fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=22, **pass_fraction=0.306**
- by_asset_class: equity 22/36, crypto **0/36**
- by_vol_regime: low 12/24, mid 6/24, high 4/24
- best_cell: p=10, atr_mult=3.0, QQQ, low-vol, Sharpe=2.88
- worst_cell: p=20, atr_mult=1.0, QQQ, high-vol, Sharpe=-0.14

## Single-config validation (Step 7)
Config: p=10, atr_mult=3.0, q=9, max_hold_days=20 (grid-best cell config).
Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.040 (pass) | 0.976 (fail, near-miss) |
| Max drawdown (<=0.25) | 0.285 (**fail**) | 0.242 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.598 (pass) | 0.418 (**fail**) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 0.75, 3/4 splits positive (pass) |
| Parameter sensitivity (atr_mult in {1,2,3}, rel std <=0.5) | 0.086 (pass) | 0.146 (pass) |
| num_trades | 293 | 290 |

Note: same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for QQQ** — full-sample Sharpe passes (1.04) but max drawdown
(0.285) breaches the 0.25 threshold; a high-frequency breakout-and-hold
rule (293 trades over the sample) with no volatility-scaled position
sizing takes on excess drawdown risk despite an attractive grid-best-cell
Sharpe (2.88 on the low-vol tercile).
**Reject for SPY** — full-sample Sharpe (0.976) narrowly misses threshold
and net-of-cost Sharpe (0.418) fails outright; the strategy trades too
frequently (290 trades) for its edge to survive a flat 10bps/trade cost
assumption.
**Reject for crypto** — 0/36 grid cells pass; consistent with nearly every
other trend/breakout strategy tested against 24/7 crypto OHLCV in this
repo.

Nothing accepted this iteration. Worth a future revisit with a wider q
(slower short_stop line, fewer whipsaw entries) or an explicit volatility-
scaled position size to address the QQQ drawdown breach specifically.

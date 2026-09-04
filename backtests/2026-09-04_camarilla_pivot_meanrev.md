# Camarilla Pivot Points Daily Mean-Reversion — Backtest Report (2026-09-04)

## Hypothesis
Camarilla pivot points (Nick Scott, 1989): 8 support/resistance levels
anchored on the prior session's close, using a Fibonacci-derived 1.1
multiplier applied to the prior day's H-L range. Source (stockgro.club)
states the core premise: price tends to mean-revert toward the
close-anchored zone unless a confirmed breakout past R4/S4 occurs, and
describes R3/S3 as the "most actively watched reversal zones"
(overbought/oversold), with R1 as the first progressive profit target.
We implement a daily-bar long-only rule: enter long when close dips below
the prior day's S3-equivalent level (entry_divisor=4 -> S3) but stays
above S4 (not a confirmed breakdown), exit when close recovers above the
prior day's R1-equivalent level (exit_divisor=12 -> R1), or a
max_hold_days time-stop.

Source: https://www.stockgro.club/blogs/trading/camarilla-pivot-points/
(web_search failed for the original query -- DDGS/RequestError -- fell
back to browser_exec Google search; a paperswithbacktest.com link from the
SERP redirected to an unrelated marketing homepage and was discarded).

## Grid summary (Step 6)
`param_grid={entry_divisor:[4.0,6.0], max_hold_days:[5,10,15]}`
(exit_divisor=12.0 fixed), symbols `{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3`, 2019-01-01..2026-09-01.

- total_cells=72, passed_cells=17, **pass_fraction=0.236**
- by_asset_class: equity 17/36, crypto **0/36**
- by_vol_regime: low 6/24, mid 0/24, **high 11/24** (notable -- unlike
  most strategies in this repo, which pass almost exclusively in the
  low-vol tercile, this mean-reversion rule picks up more passes in the
  high-vol tercile, consistent with wider intraday ranges producing
  larger/more meaningful Camarilla band deviations)
- best_cell: entry_divisor=6.0, max_hold_days=5, QQQ, low-vol, Sharpe=1.81
- worst_cell: entry_divisor=4.0, max_hold_days=5, ETH/USDT, high-vol, Sharpe=-0.26

## Single-config validation (Step 7)
Config: entry_divisor=6.0, exit_divisor=12.0, max_hold_days=5 (grid-best
cell config). Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.713 (**fail**) | 1.042 (pass) |
| Max drawdown (<=0.25) | 0.213 (pass) | 0.091 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.396 (**fail**) | 0.571 (pass) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 1.0, 4/4 splits positive (pass) |
| Parameter sensitivity (entry_divisor/max_hold_days sweep, rel std <=0.5) | 0.084 (pass) | 0.058 (pass) |
| num_trades | 205 | 205 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Accept for SPY** — all 5 standard validators pass at the grid-best
config (Sharpe 1.042, MDD 0.091, TC-survival 0.571, walk-forward perfect
4/4, parameter sensitivity very stable at 0.058).
**Reject for QQQ** — full-sample Sharpe fails (0.713) and net-of-cost
Sharpe fails (0.396) at the same config that passes on SPY; MDD and
walk-forward do pass, so the strategy isn't catastrophically broken on
QQQ, just insufficient edge net of a flat 10bps/trade cost assumption at
this trade frequency (205 trades, same as SPY).
**Reject for crypto** — 0/36 grid cells pass.

Notably this is the first strategy in this log where the high-vol tercile
contributes MORE grid passes than the low-vol tercile (11/24 vs 6/24) --
worth flagging for future loops exploring vol-regime-conditional variants
of this rule specifically.

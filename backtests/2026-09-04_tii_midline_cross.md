# Trend Intensity Index (TII) Midline Cross — Backtest Report (2026-09-04)

## Hypothesis
Trend Intensity Index (TII, M.H. Pee, Stocks & Commodities June 2002):
compute a "major" SMA (default 60), then over the trailing "minor" window
(default 30 bars) sum the positive deviations from that SMA as SDPOS and
the negative deviations as SDNEG; TII = 100*SDPOS/(SDPOS+SDNEG), a 0-100
oscillator. Source (stonehillforex.com) reframes it from a classic
overbought/oversold oscillator into a midline-cross confirmation
indicator: TII crossing above 50 is bullish confirmation. Implemented
long-only: enter on TII crossing above the 50 midline, exit on crossing
back below, or a max_hold_days time-stop.

Source: https://stonehillforex.com/2023/10/trend-intensity-index-as-a-confirmation-indicator/
(web_search failed for both original queries this iteration -- DDGS
RequestError -- fell back to browser_exec Google search, whose SERP
surfaced this article with the exact free formula and rule).

## Grid summary (Step 6)
`param_grid={minor_period:[20,30,40], max_hold_days:[15,20]}`
(major_period=60, midline=50.0 fixed), symbols
`{equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=72, passed_cells=15, **pass_fraction=0.208**
- by_asset_class: equity 15/36, crypto **0/36**
- by_vol_regime: low 11/24, mid 4/24, high 0/24
- best_cell: minor_period=40, max_hold_days=20, QQQ, low-vol, Sharpe=2.18
- worst_cell: minor_period=30, max_hold_days=15, QQQ, high-vol, Sharpe=-1.18

## Single-config validation (Step 7)
Config: minor_period=40, major_period=60, max_hold_days=20 (grid-best
cell config). Full sample 2019-01-01..2026-09-01.

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.470 (**fail**) | 0.173 (**fail**) |
| Max drawdown (<=0.25) | 0.133 (pass) | 0.176 (pass) |
| TC survival, 10bps/trade (net Sharpe>=0.5) | 0.446 (**fail**, near-miss) | 0.150 (**fail**) |
| Walk-forward, manual 4-split fallback (>=0.75 pass frac) | 0.75, 3/4 splits positive (pass) | 0.75, 3/4 splits positive (pass) |
| Parameter sensitivity (minor_period in {20,30,40}, rel std <=0.5) | 0.479 (pass, near threshold) | 0.330 (pass) |
| num_trades | 9 | 7 |

Same manual 4-equal-slice walk-forward fallback as prior iterations
(vectorbt `RangeSplitter` still broken in this install).

## Decision (Step 8)
**Reject for both QQQ and SPY** — full-sample Sharpe fails decisively on
both (0.470 and 0.173) despite the grid-best-cell figure (2.18 on QQQ
low-vol) looking attractive, the same low-vol-tercile-overstatement
pattern flagged repeatedly in this log. Net-of-cost Sharpe also fails on
both. Very low trade counts (9 and 7 over the ~7.5-year sample) mean the
midline-cross rule at these settings fires too rarely to build a robust
edge, similar to the previous iteration's VZO rejection.
**Reject for crypto** — 0/36 grid cells pass.

Nothing accepted this iteration. Similar to VZO (2026-09-04-122), the
sparse-trade-count pattern suggests midline/threshold-cross rules on
slow-moving (60/30-period) deviation-based oscillators generate too few
daily-bar signals on just 2 equity symbols to reliably clear the Sharpe
bar, even when the max drawdown and walk-forward checks pass.

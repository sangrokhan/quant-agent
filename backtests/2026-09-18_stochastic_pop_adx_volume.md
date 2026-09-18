# Stochastic Pop (Bernstein/Steckler) — ADX Range + Volume Confirmed — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "Stochastic Pop and Drop"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/stochastic-pop-and-drop,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content; original technique by Jake Bernstein, modified by
David Steckler, S&C Magazine Aug 2000): a 3-stage system -- (1) 70-day
Stochastic %K above 50 sets a bullish bias, (2) ADX(14) below a threshold
signals a range/consolidation setup phase, (3) 14-day Stochastic %K surging
above 80 with above-250-day-average volume triggers a long entry; exit when
the 14-day Stochastic drops back below 50.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/stochastic-pop-and-drop

Distinct from this repo's existing Stochastic Pop entry (2026-09-17-186,
sourced from Reddit r/pinescript: EMA-smoothed %K + non-standard 55/45
bands + EMA200 trend filter, NO ADX range stage and NO volume confirmation)
-- this is the original Bernstein/Steckler mechanism with genuine
range-detection and volume-confirmation components.

## Grid summary (Step 6)

- Grid: adx_max∈{15,20,25} × pop_level∈{75,80}, symbols={QQQ,SPY}×
  {BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 72 total cells, 23 passed (pass_fraction=0.32).
- by_asset_class: equity 8/36; crypto 15/36 (crypto shows more grid-cell
  passes here than equity, though see full-sample results below).
- by_vol_regime: low 15/24, mid 8/24, high 0/24.
- Best cell: ETH/USDT adx_max=15/pop_level=75, low-vol Sharpe=1.72.

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Best config | Full-sample Sharpe |
|---|---|---|
| QQQ | adx_max=30, pop_level=75, exit_level=40 | 1.161 |
| SPY | adx_max=25, pop_level=70, exit_level=40 | 0.676 (decisive fail) |
| BTC/USDT | adx_max=15, pop_level=75, exit_level=60 | 0.917 (fail) |
| ETH/USDT | adx_max=25, pop_level=70, exit_level=40 | 0.944 (near-miss fail) |

QQQ single-config validation (adx_max=30, pop_level=75, exit_level=40):

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.161 | ≥1.0 | PASS |
| Max drawdown | 0.159 | ≤0.25 | PASS |
| TC survival (5bps/trade, 98 trades) | 1.095 | ≥0.5 | PASS |
| Walk-forward (manual 4-slice) | 4/4=1.00 | ≥0.75 | PASS |
| Parameter sensitivity (12-combo local sweep) | rel.std=0.166 | ≤0.5 | PASS |

## Decision: ACCEPT (QQQ only)

QQQ clears all 5 validators cleanly. SPY decisively fails full-sample Sharpe
(0.676, well below any near-miss threshold). Both crypto symbols fall short
of Sharpe 1.0 as well (0.92/0.94) despite showing some grid-cell passes in
isolated vol-regime slices -- the full-sample signal isn't strong enough on
crypto with this exact rule set. This strategy is added to `strategies/` as
a live QQQ-only strategy.

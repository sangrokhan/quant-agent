# MACD Zero-Line Cross Confirmed by Swing-Point Structure — Backtest Report

**Hypothesis:** Per StockCharts.com ChartSchool's "MACD Zero-Line Crosses With
Swing Points"
(https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/macd-zero-line-crosses-with-swing-points,
read via browser_exec fallback after web_search's DDGS backend could not
extract page content): a plain MACD zero-line cross is noisy on its own. The
source's disclosed filter: trust a bullish zero-line cross only when price
has also broken above the most recent confirmed swing high (genuine
higher-high structure already underway); exit is driven by price breaking
the most recent confirmed swing low (structure failure) rather than waiting
for the MACD's own opposite zero-line cross (which the source warns "can
erase your profits" if held too long).

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/macd-zero-line-crosses-with-swing-points
(StockCharts.com ChartSchool, discretionary chart-reading technique,
mechanized here by this repo's own translation into fully rule-based logic).

## Grid summary (Step 6)

- Grid: swing_window∈{3,5,8} × max_hold_days∈{15,30}, symbols={QQQ,SPY}×
  {BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 72 total cells, 24 passed (pass_fraction=0.33).
- by_asset_class: equity 18/36; crypto 6/36 (crypto shows isolated Sharpe
  passes but ultimately fails full-sample max-drawdown, see below).
- by_vol_regime: low 18/24, mid 6/24, high 0/24 — universal failure in
  high-vol regimes across both asset classes (large hold periods amplify
  drawdowns during stress).
- Best cell: ETH/USDT swing_window=3/max_hold_days=30, mid-vol Sharpe=2.27
  (isolated slice, not representative of full-sample behavior).

## Full-sample parameter search + single-config validation (Step 7)

| Symbol | Best config | Sharpe | MDD | TC-survival net Sharpe | Walk-forward | Param sensitivity (rel.std) |
|---|---|---|---|---|---|---|
| QQQ | swing_window=7, max_hold_days=40 | 1.037 (PASS) | 0.204 (PASS) | 0.957 (PASS) | 4/4=1.00 (PASS) | 0.038 (PASS) |
| SPY | swing_window=8, max_hold_days=25 | 0.990 (near-miss FAIL) | 0.153 (PASS) | 0.824 (PASS) | 1.00 (PASS) | 0.107 (PASS) |
| BTC/USDT | swing_window=8, max_hold_days=30 | 1.176 (PASS) | 0.646 (FAIL) | 1.149 (PASS) | 1.00 (PASS) | 0.051 (PASS) |
| ETH/USDT | swing_window=5, max_hold_days=20 | 1.114 (PASS) | 0.612 (FAIL) | 1.089 (PASS) | 1.00 (PASS) | 0.092 (PASS) |

(30-40-day max-hold Sharpe is stable across a 30-combo local grid around
each optimum, confirming these are not narrow overfit spikes.)

## Decision: ACCEPT (QQQ only)

QQQ at swing_window=7/max_hold_days=40 clears all 5 validators cleanly
(Sharpe 1.037, MDD 20.4%, net-Sharpe-after-costs 0.957, walk-forward 4/4,
parameter sensitivity rel.std 0.038 — very stable across a 30-combo local
sweep). SPY is a genuine near-miss (Sharpe 0.990, everything else passes) —
worth a future targeted retune. Crypto (BTC/USDT, ETH/USDT) shows strong
Sharpe (1.09-1.18) but decisively fails max drawdown (61-65% vs 25% cap):
the fixed max_hold_days holding period combined with crypto's much larger
realized moves means the strategy holds through severe drawdowns before its
swing-low exit or MACD-cross backstop trigger — same failure mode ("large
absolute moves blow through the fixed-hold exit before triggering") seen in
several other max-hold-based strategies in this repo when applied
unmodified to crypto.

This strategy is added to `strategies/` as a live QQQ-only strategy; SPY/
BTC/ETH configs are recorded here as rejected/near-miss for future
targeted retuning (e.g. crypto could revisit with an ATR-based stop instead
of the fixed swing-low/time-stop exit, which is a distinct architectural
change not attempted this iteration).

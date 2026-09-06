# 2026-09-07: Bollinger Band Width Percentile (BBWP) Squeeze Breakout (SPY)

## Hypothesis
Ranking Bollinger Band Width (BBW = (upper-lower)/basis) as a percentile
against its own trailing lookback (BBWP, per TradingView's convention)
identifies genuinely historically-narrow volatility regimes rather than a
fixed BBW threshold. Rule (per source): BBWP<=25% = squeeze, BBWP<15% =
"tight squeeze". Enter long when a squeeze on the prior bar is followed by
a close breaking above the upper Bollinger Band; exit on close crossing
back below the basis SMA or a max_hold_days time-stop.

Source: https://kr.tradingview.com/scripts/bollingerbandstrategy/ (Pine
Script description of a BBWP overlay indicator; concrete squeeze
thresholds 25%/15% and squeeze-then-breakout entry logic used directly).

First strategy in this repo using a PERCENTILE-RANKED (not raw/fixed-
threshold) Bollinger Band Width squeeze signal, distinct from the raw
bandwidth-threshold squeeze breakout already tried in this repo
(2026-09-05-023-family "bb_bandwidth_squeeze_breakout").

## Strategy file
`strategies/2026-09-07_bbwp_squeeze_breakout.py`

## Grid test (Step 6)
`param_grid={"squeeze_pct": [15.0, 25.0, 35.0], "max_hold_days": [5, 10, 15]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **108 total cells, 10 passed (pass_fraction = 0.0926)**
- By asset class: equity 10/54, **crypto 0/54 (complete failure)**
- By vol regime: low 8/36 (best), mid 0/36, high 2/36 -- edge concentrated
  in low-vol regimes
- Best cell: `squeeze_pct=25.0, max_hold_days=5`, SPY, low-vol regime,
  Sharpe 1.455
- Worst cell: `squeeze_pct=15.0, max_hold_days=15`, SPY, mid-vol regime,
  Sharpe -0.888

## Single-config validation (Step 7) — SPY, `squeeze_pct=25.0, max_hold_days=5` (grid's best cell config), full sample

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ FAIL (near-miss) | 0.790 | ≥ 1.0 |
| Max drawdown | ✅ PASS | 0.036 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 30 trades) | ✅ PASS | 0.587 | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | ✅ PASS (borderline) | 3/4 splits positive (0.75) | ≥ 0.75 |
| Parameter sensitivity (9-combo grid) | ❌ FAIL | relative_std 0.657 | ≤ 0.5 |

## Decision: REJECTED (near-miss + parameter instability)

Sharpe misses threshold (0.79 vs 1.0) and parameter sensitivity fails
decisively -- the 9-combo grid's mean Sharpe is low (0.36) with a wide
spread (relative_std 0.657), meaning the strategy's apparent edge is
fragile to squeeze_pct/max_hold_days choices, not a robust signal. Complete
crypto failure (0/54) confirms the squeeze concept as implemented here
doesn't generalize beyond low-vol equity regimes. MDD/cost-survival/
walk-forward pass, but not enough on their own -- rejected on Sharpe +
parameter-sensitivity. Not flagged as a strong near-miss for revisit given
the parameter instability finding (unlike e.g. 2026-09-06-185's clean,
stable near-miss).

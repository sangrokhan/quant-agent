# Backtest Report: Constance Brown RSI Range-Shift Regime

**Strategy file:** `strategies/2026-09-18_constance_brown_rsi_range_shift.py`
**Date:** 2026-09-18
**Hypothesis:** Per Constance Brown's "RSI Range Rules" (corroborated
across MetaStock forum discussion, LuxAlgo's Constance Brown Studies
indicator page, and fortraders.com's RSI explainer, all read this
iteration via browser_exec fallback after Google SERP search): in a
bullish regime RSI(14) tends to range 40-80 (40 = support, not oversold);
in a bearish regime RSI(14) tends to range 20-60 (60 = resistance, not
overbought). Distinct from every fixed-threshold RSI strategy already in
this repo -- trend regime (close vs SMA(200)) determines which RSI band
is "live," and a bounce off the CURRENT regime's support level is the buy
signal. Long-only: only trades the bull-regime dip-buy side.

## Grid summary (Step 6)

Parameter grid: `bull_support_level` in {35,40,45}, `trend_window` in
{150,200}; symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT};
vol_regime_splits=3; sample 2016-01-01 to 2026-09-01.

- Total cells: 72, passed: 12, **pass_fraction = 0.167**
- By asset class: equity 12/36 passed, crypto **0/36** (decisively
  rejected)
- By vol regime: **low 12/24, mid 0/24, high 0/24** -- edge concentrated
  entirely in low-vol regime
- Best cell: equity SPY low-vol, bull_support_level=40/trend_window=150,
  Sharpe=2.62
- Best average equity config: bull_support_level=40, trend_window=200
  (mean Sharpe 1.02 across its 6 equity cells)

## Single-config validation (Step 7): bull_support_level=40, trend_window=200

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample, 2016-2026) | 0.804 | 0.865 | >= 1.0 | **FAIL both** |
| Max drawdown | 0.208 | 0.164 | <= 0.25 | PASS both |
| Net Sharpe after costs (5bps/trade) | 0.788 | 0.839 | >= 0.5 | PASS both |
| Walk-forward (4-split, manual) | 3/4 splits positive | 2/4 splits positive | >= 0.75 frac | **QQQ PASS, SPY FAIL** |
| Parameter sensitivity (6-value local sweep, relative std) | 0.488 | 0.483 | <= 0.5 | PASS both (barely) |

## Decision: REJECT

Full-sample Sharpe fails on both primary equity symbols (QQQ 0.804, SPY
0.865), and SPY additionally fails walk-forward (only 2/4 splits
positive). The grid confirms this is a low-vol-regime-only effect (12/24
low-vol pass vs 0/24 in both mid and high vol) with a very low trade count
(31-35 trades over the full 2016-2026 sample) -- the strategy is simply
too infrequent and too regime-narrow to clear the Sharpe bar on a blended
full-sample basis despite an attractive low-vol-only Sharpe (up to 2.62).
Crypto is decisively rejected (0/36). Parameter sensitivity is a marginal
pass (relative std just under 0.5 for both symbols) -- another sign the
edge is fragile to the exact threshold choice.

Strategy file and this report are kept as a rejected-attempt record.

# Backtest Report: IBS + RSI(21) "Classical" Mean Reversion (2026-09-26)

**Strategy file:** `strategies/2026-09-26_ibs_rsi21_classical_meanrev.py`
**KB id:** 2026-09-26-009

## Hypothesis

QuantifiedStrategies.com's "S&P 500 Mean Reversion Using IBS and RSI:
Classical Approach" (https://quantifiedstrategies.substack.com/p/s-and-p-500-mean-reversion-using-541
— disclosed rule quoted verbatim in the public search snippet; full
article body is paywalled):

1. IBS = (Close-Low)/(High-Low) must be below `ibs_threshold` (0.25 default).
2. RSI(`rsi_window`=21) must be below `rsi_threshold` (45 default).
3. Both true simultaneously -> long at close.
4. Exit when close > yesterday's close.

Added `max_hold_days=15` safety time-stop (source's own rule has no
explicit time-stop). Distinct from all prior IBS-family KB entries, which
pair IBS with RSI(2)/RSI(3)/RSI(5) fast oscillators or a 200-SMA trend
filter — this is the first slow RSI(21) confirmation with no trend filter.

## Grid test (Step 6)

`ibs_threshold` in {0.2, 0.25, 0.3} x `rsi_threshold` in {40, 45, 50},
symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3,
2016-2026 (108 cells):

- **pass_fraction = 0.287 (31/108)**
- by_asset_class: equity 22/54, crypto 9/54
- by_vol_regime: low 5/36, mid 0/36, high 26/36 (edge concentrated in
  high-realized-vol periods — mean reversion works best when ranges are wide)
- best_cell: `ibs_threshold=0.3, rsi_threshold=40`, QQQ, high-vol, Sharpe 2.45
- worst_cell: `ibs_threshold=0.25, rsi_threshold=40`, BTC/USDT, low-vol, Sharpe -0.98

## Single-config validation (Step 7)

Config: `ibs_threshold=0.3, rsi_threshold=40, rsi_window=21, max_hold_days=15`,
full sample 2016-2026.

| Metric | QQQ | SPY |
|---|---|---|
| Sharpe | **1.419** (pass, ≥1.0) | 0.772 (**fail**, <1.0) |
| Max Drawdown | 0.071 (pass, ≤0.25) | 0.104 (pass, ≤0.25) |
| Net Sharpe after 10bps costs | 1.315 (pass, ≥0.5) | 0.689 (pass, ≥0.5) |
| Walk-forward (manual 4-split, vectorbt RangeSplitter broken) | 1.0 (pass, ≥0.75) | 1.0 (pass, ≥0.75) |
| Parameter sensitivity (rel. std, 9-cell local grid) | 0.101 (pass, ≤0.5) | 0.156 (pass, ≤0.5) |
| num_trades | 57 | 50 |

## Decision

**ACCEPT for QQQ only** (all 5 validators pass). **REJECT for SPY**
(near-miss, Sharpe 0.772 vs 1.0 threshold — everything else passes cleanly,
flagged as a near-miss worth revisiting with a wider/narrower parameter
neighborhood in a future iteration). Crypto not validator-tested at the
single-config stage given the grid's decisive weak crypto pass rate (9/54,
17%) and negative worst-cell Sharpe on BTC/USDT.

## Source

https://quantifiedstrategies.substack.com/p/s-and-p-500-mean-reversion-using-541
(snippet-disclosed rule) — read via `web_search`, snippet content only
(article body paywalled, confirmed via `browser_exec` visit).

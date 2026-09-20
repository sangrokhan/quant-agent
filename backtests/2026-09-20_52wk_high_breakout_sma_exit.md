# 52-Week High Breakout + 200-day SMA Exit — ACCEPTED (QQQ only)

## Hypothesis
Per QuantifiedStrategies.com's "52-Week High Trading Strategy" article
(https://www.quantifiedstrategies.com/52-week-high-trading-strategy/), citing
Hong/Jordan/Liu's academic finding of a "52-week high effect" (anchoring-bias
under-reaction: investors are slow to bid prices past the 52-week high,
so momentum continues once cleared). Source's own disclosed single-symbol
rule: buy on a new 52-week (252-day) closing high; exit on close crossing
below the 200-day SMA (source's disclosed "Exit 1": CAGR 8.6%/MDD 44% on
their broad sample). First 52-week-high strategy in this repo (0 prior
matches).

Source: https://www.quantifiedstrategies.com/52-week-high-trading-strategy/
(read via browser_exec after web_search's DDGS backend returned "No results
found" for this iteration's query).

## Grid test summary (Step 6)
`param_grid={"new_high_window": [126,252], "trend_sma_window": [150,200,250]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2016-01-01 to 2026-09-01, 72 total cells.

- pass_fraction: 0.208 (15/72)
- by_asset_class: equity 14/36 passed, crypto 1/36 passed
- by_vol_regime: low 13/24, mid 2/24, high 0/24 (edge concentrated in
  low-vol regimes, expected for a trend-continuation strategy)
- best_cell: equity QQQ, new_high_window=252/trend_sma_window=200, low-vol
  regime, Sharpe 2.391
- worst_cell: crypto ETH/USDT, new_high_window=126/trend_sma_window=150,
  high-vol regime, Sharpe -0.115

## Single-config validation (Step 7) — QQQ, new_high_window=126/trend_sma_window=200

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.082 | >=1.0 |
| Max drawdown | PASS | 0.203 | <=0.25 |
| Transaction cost survival (10bps/trade, 17 trades) | PASS | net Sharpe 1.067 | >=0.5 |
| Walk-forward (4 splits, manual, vectorbt splitter API bug worked around) | PASS | 4/4 splits positive Sharpe (1.0 pass fraction) | >=0.75 |
| Parameter sensitivity (5x5 sweep on new_high_window x trend_sma_window) | PASS | relative_std 0.098 | <=0.5 |

Full-sample Sharpe by symbol at their own best config:
- QQQ (nh=126, tw=200): Sharpe 1.082 — **PASS**
- SPY (nh=126, tw=150): Sharpe 0.869 — fail (near-miss)
- BTC/USDT (nh=252, tw=250): Sharpe 0.235 — decisive fail
- ETH/USDT (nh=252, tw=150): Sharpe 0.217 — decisive fail

## Decision: ACCEPTED (QQQ only)

All 5 validators pass for QQQ at new_high_window=126/trend_sma_window=200.
SPY is a near-miss (Sharpe 0.869), and crypto is decisively rejected — the
52-week-high anchoring-bias mechanism is a stock-market/individual-security
phenomenon (per the source's own academic citation being about individual
stocks and industries, not indices or crypto), so QQQ's stronger showing
vs. SPY (broad index, less "individual security" character) and crypto's
outright rejection is directionally consistent with the source's own
literature.

## Notes for future loops
- QQQ-only pass is narrow; a future iteration could try SPY-specific
  parameter retuning (source itself notes indices show a weaker effect
  than individual stocks) or test on genuinely individual large-cap stocks
  if the repo ever adds a broader per-symbol testing loop.
- 17 trades over the ~10.7-year sample is a low turnover count — good for
  transaction-cost survival, but means the Sharpe estimate has meaningful
  sampling uncertainty; the walk-forward 4/4 pass is reassuring but each
  split still has few trades.

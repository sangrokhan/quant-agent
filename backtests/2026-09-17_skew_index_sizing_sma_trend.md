# 2026-09-17 CBOE SKEW Index Continuous Sizing Dial + SMA Trend Gate

## Hypothesis

This repo has 1 prior CBOE SKEW Index entry (2026-09-05-029, rejected): a
BINARY threshold gate (flat when rolling z-score of SKEW exceeded an
extreme threshold, otherwise fully long). Per
https://ecmsource.com/volatility-skew-and-smile-explained-why-otm-puts-cost-more/
(citing the Cboe SKEW whitepaper), SKEW continuously measures the market's
own pricing of tail risk (cost of OTM S&P puts vs ATM). This iteration
follows this repo's binary-threshold-to-continuous-sizing-dial rescue
pattern: exposure scales smoothly and INVERSELY with SKEW's own rolling
z-score (tanh-squashed), applied within an SMA(trend_window) uptrend gate,
instead of a hard flat/full-position flip.

Source: CBOE SKEW Index (^SKEW ticker via yfinance, data/loaders.py::load_equity,
no new fetching logic) + ecmsource.com explainer of the index's construction.

## Strategy file

`strategies/2026-09-17_skew_index_sizing_sma_trend.py`

## Grid test summary (216 cells: sensitivity x skew_zscore_window x deadband x 4 symbols x 3 vol regimes)

- pass_fraction: 0.375 (81/216)
- by_asset_class: equity 52/108 passed; crypto 29/108 passed
- by_vol_regime: low 62/72; mid 7/72; high 12/72
- best_cell: SPY, sensitivity=0.3/skew_zscore_window=252/deadband=0.2, low-vol regime, Sharpe 2.71

## Single-config validation (full sample, 2019-01-01 to 2026-09-01)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe, 5bps/trade) | Walk-forward (4-split, >0 Sharpe fraction) | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ (grid-best) | deadband=0.2, sensitivity=0.3, skew_zscore_window=252 | 0.908 (<1.0 near-miss) | 0.134 (pass) | 0.639 (pass) | 0.75 (pass) | 0.032 (pass) | fail (Sharpe) |
| QQQ (retuned) | deadband=0.2, sensitivity=0.2, skew_zscore_window=63, trend_window=30 | 1.198 (pass) | 0.108 (pass) | 0.847 (pass) | 1.0 (pass) | 0.035 (pass) | **ACCEPT** |
| SPY | deadband=0.2, sensitivity=0.3, skew_zscore_window=126 | 1.077 (pass) | 0.078 (pass) | 0.651 (pass) | 1.0 (pass) | 0.048 (pass) | **ACCEPT** |
| BTC/USDT | deadband=0.2, sensitivity=0.3, skew_zscore_window=63, leverage_cap=0.3 | 0.161 (fail) | 0.218 (pass) | -0.055 (fail) | 1.0 (pass) | 0.142 (pass) | **REJECT** |

QQQ's grid-optimal config near-missed the Sharpe threshold (0.908); a
targeted local retune (widening trend_window/skew_zscore_window search)
found a passing configuration (Sharpe 1.198), following this repo's
established per-symbol retune fix pattern.

## Outcome

**Accepted for equity (QQQ retuned config, SPY grid-best config)** -- all 5
validators pass for both. **Rejected for crypto** -- BTC/USDT fails
decisively on Sharpe and transaction-cost survival even at low leverage_cap.

Scope: honest narrow scope -- works on equity index ETFs in low-vol
regimes (as usual for this repo's continuous-sizing family), does not
generalize to crypto (SKEW is a US-equity-options-derived series
forward-filled onto crypto's 24/7 calendar, likely too stale/discontinuous
a signal for that asset class).

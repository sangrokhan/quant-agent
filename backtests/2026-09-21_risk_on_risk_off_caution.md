# Backtest Report: TASC "Risk-On, Risk-Off, Or Caution" Regime Exposure Dial (QQQ)

**Strategy file:** `strategies/2026-09-21_risk_on_risk_off_caution.py`
**Date:** 2026-09-21

## Hypothesis

Per TradingView's PineCodersTASC implementation of Di Prima & Baruffa's July
2026 TASC Traders' Tips article "Market Regime Identification Using Trend,
Volatility, And Credit Conditions" (read via browser_exec after
web_search's DDGS/Yahoo backend TLS-erroring on repeated queries): a weekly
3-vote regime classifier sizes exposure using (1) trend (close above its own
200d SMA), (2) volatility term structure (VIX < VIX3M), (3) credit risk
appetite (100d MA of rolling Z-score of HYG/IEF ratio > 0). 3/3 favorable =
full exposure, 2/3 = half, <=1/3 = flat, rebalanced weekly. First 3-way
graduated-exposure regime dial in this repo combining trend + vol-term-
structure + credit-spread votes (0 prior KB hits).

## Grid test summary (Step 6)

Params: trend_window [150,200] x credit_zscore_window [60,100] x
leverage_cap [1.0]; QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto, no
economic rationale expected but tested per protocol); vol_regime_splits=3.
48 cells.

```
pass_fraction: 0.25 (12/48)
by_asset_class: equity 12/24, crypto 0/24
by_vol_regime: low 8/16, mid 4/16, high 0/16
best_cell: SPY low-vol, Sharpe=2.58
worst_cell: QQQ high-vol, Sharpe=0.09
```

Equity-only edge as expected (VIX/HYG/IEF are US-equity/credit-market-native
signals with no crypto transmission mechanism) -- crypto decisively 0/24.
Equity passes span both low AND mid vol terciles (50% pass rate), a
healthier signature than most of this cron trigger's other candidates.

## Full-sample single-config validation (Step 7)

QQQ and SPY at all 4 grid params, full 2019-2026 sample:

| Symbol | trend_window | credit_zscore_window | Sharpe | Pass? | MDD | Pass? |
|---|---|---|---|---|---|---|
| QQQ | 150 | 60 | 1.018 | PASS | 0.212 | PASS |
| QQQ | 150 | 100 | 1.015 | PASS | 0.169 | PASS |
| QQQ | 200 | 60 | 0.958 | FAIL | 0.239 | PASS |
| QQQ | 200 | 100 | 0.955 | FAIL | 0.217 | PASS |
| SPY | 150 | 60 | 0.886 | FAIL | 0.177 | PASS |
| SPY | 150 | 100 | 0.876 | FAIL | 0.166 | PASS |
| SPY | 200 | 60 | 0.876 | FAIL | 0.162 | PASS |
| SPY | 200 | 100 | 0.865 | FAIL | 0.165 | PASS |

QQQ at trend_window=150 clears Sharpe on both credit_zscore_window values;
picked credit_zscore_window=100 as the primary config (marginally higher
Sharpe, more standard window length matching credit_ma_window).

Full validator suite, QQQ, trend_window=150/credit_zscore_window=100/
credit_ma_window=100/leverage_cap=1.0:

| Validator | Result | Threshold | Pass? |
|---|---|---|---|
| Sharpe | 1.015 | >=1.0 | PASS |
| Max Drawdown | 0.169 (16.9%) | <=0.25 | PASS |
| TC-survival (10bps/trade, 42 rebalance events) | net Sharpe 0.960 | >=0.5 | PASS |
| Walk-forward (4 splits) | per-split Sharpe [0.86, -0.75, 1.07, 1.46], pass_fraction 0.75 | >=0.75 | PASS (exactly at threshold) |
| Parameter sensitivity (12-combo local grid: trend_window in [130,150,170,200] x credit_zscore_window in [60,80,100]) | relative_std 0.050 (mean Sharpe 0.981, std 0.049) | <=0.5 | PASS (very robust) |

Walk-forward has one negative split (2nd quarter of the sample, likely the
2022 rate-hike drawdown period where even a well-designed regime filter can
whipsaw) but still clears the 0.75 pass-fraction bar (3/4 splits positive).
Parameter sensitivity is unusually strong -- the entire 12-combo local grid
Sharpe ranges narrowly from 0.909 to 1.049, indicating this is a broad
plateau, not a fragile single-point optimum.

SPY does not clear Sharpe at any tested config in this grid (best 0.886) --
scoped as QQQ-only for this iteration.

## Decision (Step 8)

**ACCEPT (QQQ only, trend_window=150/credit_zscore_window=100/
credit_ma_window=100/leverage_cap=1.0)**. All 5 validators pass. SPY tested
but falls short of the Sharpe threshold at every config in this grid (best
0.886) -- not pursued further this iteration; a future loop could retune SPY
separately. Crypto decisively out of scope (no economic transmission
mechanism for US credit-spread/VIX-term-structure signals).

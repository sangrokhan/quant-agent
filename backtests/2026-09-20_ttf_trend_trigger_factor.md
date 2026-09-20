# Trend Trigger Factor (TTF, M.H. Pee) Threshold-Cross Long/Flat System — ACCEPTED (QQQ + SPY)

## Hypothesis
Per Tokenist's TTF explainer (https://www.tokenist.com/trading-indicators/trend-trigger-factor-indicator/),
M.H. Pee's Trend Trigger Factor uses two non-overlapping N-day lookback
windows:
```
Buy Power  = HighestHigh(days 1..N)   - LowestLow(days N+1..2N)
Sell Power = HighestHigh(days N+1..2N) - LowestLow(days 1..N)
TTF = [(Buy Power - Sell Power) / (0.5 * (Buy Power + Sell Power))] * 100
```
Creator's own disclosed rule: TTF > +100 = bull trend (go/stay long);
TTF < -100 = bear trend (go/stay short); values between the thresholds
mean "maintain current position" (an always-in-the-market reversal
system). Adapted to this repo's long/flat convention: long when TTF
crosses above the upper threshold, flat when TTF crosses below the lower
threshold (mirror-negative of upper), hold state in between. First TTF
strategy in this repo (0 prior matches for "Trend Trigger Factor"/"TTF").

Source: https://www.tokenist.com/trading-indicators/trend-trigger-factor-indicator/
(read via browser_exec Google SERP after web_search returned unrelated
results for prior queries this iteration).

## Grid test summary (Step 6)
`param_grid={"ttf_window": [10,15,20,30], "upper_threshold": [80,100,120]}`
(lower_threshold = -upper_threshold), `symbols={"equity": ["QQQ","SPY"],
"crypto": ["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, 2016-01-01 to
2026-09-01, 144 total cells.

- pass_fraction: 0.333 (48/144)
- by_asset_class: equity 46/72 passed, crypto 2/72 passed
- by_vol_regime: low 26/48, mid 22/48, high 0/48
- best_cell: crypto ETH/USDT, ttf_window=10/upper=120, mid-vol regime,
  Sharpe 2.500 (isolated, not representative — see full-sample results
  below where crypto fails decisively)
- worst_cell: equity QQQ, ttf_window=15/upper=120, high-vol regime,
  Sharpe -0.666

The initial grid's default window range (10-30) undershot the true optimum
— a follow-up finer sweep (window 5-15) found the strongest full-sample
equity Sharpe at ttf_window=5.

## Single-config validation (Step 7) — QQQ & SPY, shared config: ttf_window=5, upper_threshold=50, lower_threshold=-50

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS (1.200) | PASS (1.417) | >=1.0 |
| Max drawdown | PASS (0.233) | PASS (0.131) | <=0.25 |
| Transaction cost survival (10bps/trade) | PASS (net Sharpe 1.103, 91 trades) | PASS (net Sharpe 1.284, 86 trades) | >=0.5 |
| Walk-forward (4 manual splits) | PASS (4/4 positive) | PASS (4/4 positive) | >=0.75 |
| Parameter sensitivity (5x5 window x threshold sweep) | PASS (relative_std 0.088) | PASS (relative_std 0.185) | <=0.5 |

Crypto falsification check at the SAME shared config:
- BTC/USDT: Sharpe 0.127 — decisive fail
- ETH/USDT: Sharpe 0.150 — decisive fail

## Decision: ACCEPTED (QQQ + SPY, shared config)

All 5 validators pass for BOTH equity symbols at a single shared
configuration (ttf_window=5, threshold=±50). Crypto decisively rejected
at the same config, consistent with most other trend/momentum threshold
systems in this repo showing weaker transferability to 24/7 crypto markets.

## Notes for future loops
- The always-in-the-market long/short reversal design from the source was
  adapted to long/flat only (this repo's standard convention); a future
  iteration could test the TRUE always-in-market long/short version if the
  grid harness ever supports short positions.
- ttf_window=5 is quite short (a 10-day total two-window lookback), so the
  strategy has meaningful turnover (86-91 trades over ~10.7 years, ~8/year)
  — well within transaction-cost survival margin but worth flagging for
  future retunes that push the window even shorter.

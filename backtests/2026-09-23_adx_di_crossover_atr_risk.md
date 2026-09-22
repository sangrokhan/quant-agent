# 2026-09-23 ADX/DMI DI+/DI- Crossover with ADX Threshold Gate + ATR Risk (SPY/QQQ/BTC/ETH)

## Hypothesis
Source: Google AI Overview (Korean-language SERP, English answer content;
search: "ADX DI+ DI- crossover trend strategy specific threshold rule
backtest"), read via browser_exec Google SERP fallback (web_search DDGS
backend errored this query). `suggested_workload=light`.

Rule (J. Welles Wilder's classic ADX/DMI system with specific numeric
thresholds): long entry when DI+ crosses above DI- AND ADX >= 25 (trend
strength confirmation); exit on the opposite DI crossover, OR ADX breaking
below 20 (trend regime failure), OR a 1.5x ATR stop-loss / 2:1
reward:risk take-profit (whichever hits first).

## Grid test summary (adx_entry_threshold x [20,25], reward_risk x
[1.5,2.0]; symbols QQQ equity, BTC/USDT crypto; vol_regime_splits=3;
24 total cells)

- pass_fraction: 0.208 (5/24)
- by_asset_class: equity 5/12, crypto 0/12 (crypto failed entirely)
- by_vol_regime: low 4/8, mid 1/8, high 0/8
- best_cell: adx_entry_threshold=20, reward_risk=1.5, equity QQQ, low-vol,
  Sharpe 2.03
- worst_cell: adx_entry_threshold=20, reward_risk=1.5, crypto BTC/USDT,
  low-vol, Sharpe -1.33

## Single-config validation (full-period, unconditional, full grid sweep
including SPY/ETH)

| Config | Symbol | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|---|---|---|---|---|---|
| adx=25, rr=2.0 | SPY | 0.929 | No (near-miss) | 0.068 | Yes |
| adx=20, rr=2.0 | SPY | 0.794 | No | 0.099 | Yes |
| adx=25, rr=1.5 | SPY | 0.755 | No | 0.068 | Yes |
| adx=25, rr=2.0 | QQQ | 0.731 | No | 0.048 | Yes |
| adx=20/25, rr=1.5/2.0 | BTC | -0.056 to 0.011 | No | 0.363-0.520 | No |
| adx=20/25, rr=1.5/2.0 | ETH | -0.020 to 0.075 | No | 0.298-0.475 | No |

## Verdict: REJECTED (second near-miss this cron trigger, equity only)

Best full-period Sharpe (SPY, adx_entry_threshold=25, reward_risk=2.0) is
0.929 -- a near-miss just under the 1.0 threshold, similar in character to
this trigger's earlier TRIX near-miss (2026-09-23-031, SPY 0.983). Unlike
TRIX, the ADX/DMI crossover works ONLY on equities (SPY/QQQ); crypto
(BTC/USDT, ETH/USDT) fails decisively with negative-to-near-zero Sharpe and
excessive max drawdown (36-52%, violating the 0.25 MDD threshold too).
Walk-forward/tx-cost/parameter-sensitivity validators skipped given light
workload and the clear near-miss.

Strategy file kept in `strategies/` as a rejected-but-close record. Given
this cron trigger already produced ONE lesson from attempting to "rescue" a
near-miss via an explicit vol-regime gate that backfired (2026-09-23-032),
a future loop revisiting this ADX near-miss should test alternative
rescue angles carefully and as isolated variables (e.g. wider adx_window,
tighter/looser ADX exit threshold, or ATR-window tuning) rather than
assuming any single "obvious" fix (like a vol gate) will help without
testing it explicitly.

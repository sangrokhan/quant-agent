# 2026-09-23 RVI Signal-Line Crossover + 200-SMA Trend Filter (SPY/QQQ/BTC/ETH)

## Hypothesis
Source: Google AI Overview (Korean-language SERP; search: "Relative Vigor
Index RVI signal line crossover strategy specific rule backtest"), read via
browser_exec Google SERP fallback (web_search DDGS backend errored this
query). `suggested_workload=light`.

Rule: RVI(10) (close-open / high-low, 4-bar SWMA-smoothed, summed over 10
bars per standard formula) crossing above its own 4-bar SWMA signal line,
gated by price being above a 150/200-day SMA trend filter (per the
source's own explicit warning that naive crossover-only trading whipsaws
badly in ranging markets); exit on the reverse crossover.

## Grid test summary (rvi_window x [10,14], trend_sma_window x [150,200];
symbols QQQ equity, BTC/USDT crypto; vol_regime_splits=3; 24 total cells)

- pass_fraction: 0.417 (10/24) -- the strongest pass fraction of this cron
  trigger's 7 candidates
- by_asset_class: equity 8/12, crypto 2/12
- by_vol_regime: low 4/8, mid 6/8, high 0/8
- best_cell: rvi_window=10, trend_sma_window=150, equity QQQ, low-vol,
  Sharpe 2.10
- worst_cell: rvi_window=14, trend_sma_window=150, equity QQQ, high-vol,
  Sharpe -1.16

## Single-config validation (full-period, unconditional, full grid sweep
incl. SPY/ETH)

| Config | Symbol | Sharpe | Passed (>=1.0) | Max DD | Passed (<=0.25) |
|---|---|---|---|---|---|
| rvi=14, sma=200 | SPY | 0.931 | No (near-miss) | 0.099 | Yes |
| rvi=10, sma=200 | QQQ | 0.827 | No | 0.283 | No |
| rvi=14, sma=150 | SPY | 0.734 | No | 0.099 | Yes |
| all crypto configs | BTC/ETH | 0.06-0.13 | No | 0.43-0.66 | No |

## Verdict: REJECTED (third near-miss this cron trigger, equity only)

Best full-period Sharpe (SPY, rvi_window=14, trend_sma_window=200) is
0.931 -- another close near-miss, in the same range as this trigger's TRIX
(0.983) and ADX-DI (0.929) near-misses. Crypto fails decisively on both
Sharpe (<0.14) and max drawdown (0.43-0.66, far over the 0.25 threshold).
Walk-forward/tx-cost/parameter-sensitivity validators skipped given light
workload and the clear near-miss.

Strategy file kept in `strategies/` as a rejected-but-close record. This
cron trigger has now produced THREE independent equity-only near-misses
(TRIX 0.983, ADX-DI 0.929, RVI 0.931) all clustered in the 0.92-0.98 Sharpe
range on SPY specifically, all using different oscillator families but a
common shape: momentum-oscillator-crosses-its-own-smoothed-signal-line,
gated by SOME form of longer-term trend/EMA/SMA filter. This is a notable
pattern worth flagging for a future loop: rather than tuning any ONE of
these oscillators further, a future iteration could test whether SPY's
0.9x-range Sharpe ceiling across these oscillator-crossover-plus-trend-
filter designs reflects a structural limit of this exact strategy SHAPE
(oscillator zero/signal-cross + static long-only trend filter) on SPY daily
bars over 2019-2026, rather than a fixable parameter/indicator-family
detail -- e.g. by testing whether adding a transaction-cost-aware holding
period minimum, or blending 2-3 of these near-miss signals as a majority-
vote ensemble, pushes the combined signal over the Sharpe 1.0 bar where
none does individually.

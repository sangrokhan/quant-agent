# Ehlers Correlation Trend Indicator (CTI) Dual-Period Crossover

**Hypothesis:** Per John Ehlers' "Correlation Trend Indicator" (Stocks &
Commodities Magazine, 05/2020), transcribed at
https://www.prorealcode.com/prorealtime-indicators/ehlers-unique-correlation-trend-indicator-cti/ :
CTI is the Pearson correlation of the price curve against an ideal straight
uptrend line over a rolling window (bounded [-1,+1]). The article/author
note a dual-period crossover system: "buy when the 5 day CTI crosses over
the 10 day CTI when both values are below -0.5 threshold ... and vice versa
for the short entry." We test the long-only version: long on a bullish
short/long CTI crossover with both below `-corr_threshold`, exit on the
mirror bearish crossover with both above `+corr_threshold`, or a
`max_hold_days` time-stop.

Source: https://www.prorealcode.com/prorealtime-indicators/ehlers-unique-correlation-trend-indicator-cti/
(logged in `knowledge_base/visited_pages.jsonl`)

## Step 6 — Grid test (short_period in {5,8}, long_period in {10,20},
corr_threshold in {0.4,0.5,0.6}, equity={QQQ,SPY}, crypto={BTC/USDT,
ETH/USDT}, vol_regime_splits=3, 2019-01-01 to 2026-09-01)

- Total cells: 144, passed: 6, **pass_fraction = 0.042**
- By asset class: equity 6/72 passed, **crypto 0/72 passed** (decisive fail)
- By vol regime: low 0/48, mid 3/48, high 3/48
- Best cell: QQQ, short_period=5, long_period=20, corr_threshold=0.6,
  high-vol regime, Sharpe 1.854 (also strong in mid-vol: Sharpe 1.769)
- Worst cell: QQQ, short_period=8, long_period=10, corr_threshold=0.4,
  mid-vol regime, Sharpe -1.224

The grid immediately flags a red flag: per-param-combo full-sample-avg
Sharpe **flips sign** just by moving `long_period` from 10 to 20 at fixed
`short_period`/`corr_threshold` (e.g. short=5/thr=0.5: long=10 avg Sharpe
-0.117 vs long=20 avg Sharpe +0.891) — a strong early signal that Step 7's
parameter-sensitivity check would fail.

## Step 7 — Single-config validators (short_period=5, long_period=20,
corr_threshold=0.6, max_hold_days=15, QQQ, full 2019-2026 sample)

| Validator | Result |
|---|---|
| Sharpe (>= 1.0) | PASS 1.401 |
| Max Drawdown (<= 0.25) | PASS 0.170 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade, 26 trades) | PASS 1.361 |
| Walk-forward (manual 4-split, sharpe>0 required, since `check_walk_forward` hits the pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version) | PASS 4/4 splits positive |
| Parameter sensitivity (relative_std <= 0.5, over the 12 QQQ param combos from Step 6's grid, avg Sharpe across vol regimes per combo) | **FAIL relative_std 2.60** (mean 0.179, std 0.466 — driven by combos with `long_period=10` averaging *negative* Sharpe while `long_period=20` combos average strongly positive) |

## Outcome: **REJECTED**

Sharpe/MDD/transaction-cost-survival/walk-forward all pass cleanly for the
single best config (QQQ, short_period=5/long_period=20/corr_threshold=0.6),
but parameter sensitivity decisively fails: the strategy's edge is
concentrated in a narrow corner of parameter space (`long_period=20`
specifically) and flips to a loss with `long_period=10`, which the raw
Step-6 grid numbers confirm directly (not an artifact of the sensitivity
metric's aggregation). This is consistent with the source article's own
caveat that CTI crossover trading "would be difficult" and "too weak for
being directly exploited" — our grid empirically reproduces that caution.
Crypto is a decisive 0/72 fail across the whole grid; low-vol regime is a
decisive 0/48 fail.

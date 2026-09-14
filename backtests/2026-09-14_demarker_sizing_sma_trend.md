# Backtest report: DeMarker Continuous Sizing on SMA(40) Trend Gate

**Strategy file:** `strategies/2026-09-14_demarker_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-132
**Source:** https://tradersunion.com/interesting-articles/forex-indicators-for-traders/demarker-indicator/
(visited via browser_exec fallback after `web_search` DDGS backend TLS/connection
error on the query "DeMarker indicator formula bounded 0 1 trading strategy";
confirmed via Google SERP result links plus direct page read: DeMarker is a
Tom DeMark momentum oscillator, bounded [0,1], comparing current high/low to
previous bar's high/low to gauge buying/selling pressure exhaustion).

## Hypothesis

DeMarker (Tom DeMark): `DeMax_t = max(high_t - high_{t-1}, 0)`,
`DeMin_t = max(low_{t-1} - low_t, 0)`; `DeM = SMA(DeMax, n) / (SMA(DeMax, n) + SMA(DeMin, n))`,
naturally bounded [0, 1], centerline 0.5. This repo has 2 prior DeMarker
entries (2026-09-04-154 accepted binary oversold-bounce/overbought-exit
crossover; 2026-09-10-126 divergence variant), both binary entry/exit
constructions. This iteration reframes the already-[0,1]-bounded DeM value
directly (no z-score needed, unlike unbounded oscillators) as a CONTINUOUS
SIZING dial: `(DeM - 0.5) * 2` rescales to [-1, 1], scaled by `sensitivity`
and added to `base_exposure`, clipped to `[0, leverage_cap]`, gated by an
SMA(trend_window) uptrend filter, with an exposure-change deadband to
control turnover -- reusing this cron trigger's validated continuous-
sizing-dial pattern (19+ prior indicator families tested this way).

## Step 6 grid summary (`grid_result_demarker_sizing.json`)

- Grid: `sensitivity in [0.5, 1.0]` x `deadband in [0.15, 0.25]` x
  `leverage_cap in [0.4, 1.0]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
  (crypto), `vol_regime_splits=3` (low/mid/high realized-vol terciles).
- **96 cells total, 50 passed -- pass_fraction 0.521.**
- By asset class: equity 24/48 (0.50), crypto 26/48 (0.542).
- By vol regime: low 30/32 (0.94), mid 16/32 (0.50), high 4/32 (0.125) --
  strong low-vol edge, degrades sharply in high-vol regimes (consistent
  with the trend-gate + sizing-dial mechanism being a trend-following
  construction that struggles in choppy/high-vol conditions).
- Best cell: QQQ, sensitivity=1.0/deadband=0.25/leverage_cap=1.0, low-vol,
  Sharpe 2.95.

## Step 7 single-config validators (`validators_demarker_sizing.json`)

Primary config search found deadband=0.25 gave QQQ a transaction-cost-
survival near-miss (net Sharpe 0.442 vs 0.5 threshold, 283 trades); widening
deadband to 0.30 fixed it by cutting turnover to 226 trades.

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens. | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | sens=1.0, db=0.30, lev=1.0 | 1.084 (pass) | 0.142 (pass) | 0.606 (pass) | 1.00 (pass) | 0.040 (pass) | **ACCEPT** |
| SPY | sens=1.0, db=0.30/0.35/0.40, lev=1.0 | 0.75-0.93 (fail all) | n/a | 0.32-0.61 (fail at 0.30/0.35) | not run | not run | **REJECT** (no passing deadband found in 0.30-0.40 sweep) |
| BTC/USDT | sens=1.0, db=0.25, lev=0.4 | 1.447 (pass) | 0.222 (pass) | 1.228 (pass) | 1.00 (pass) | 0.022 (pass) | **ACCEPT** |
| ETH/USDT | sens=1.0, db=0.25, lev=0.4 | 1.329 (pass) | 0.206 (pass) | 1.200 (pass) | 1.00 (pass) | 0.012 (pass) | **ACCEPT** |

## Decision

**Partial accept**: QQQ + BTC/USDT + ETH/USDT all 5 validators pass.
SPY rejected -- genuine but non-trivial near-miss (Sharpe stuck 0.75-0.93
across a deadband sweep 0.30-0.40, TC-survival also fails at the lower end);
did not find a passing SPY config within this iteration's budget. Flagged
for a possible follow-up per-symbol retune (shorter trend_window or
different demarker_period), following the pattern of several other
accepted-QQQ/rejected-SPY entries this cron trigger (KST, Fisher Transform).
Crypto required leverage_cap=0.4 to pass MDD, consistent with this cron
trigger's leverage-cap-aware crypto methodology established in prior
iterations (2026-09-14-124/125).

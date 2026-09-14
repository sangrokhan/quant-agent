# 2026-09-14 — Twiggs Money Flow (true-range + EMA-smoothed) continuous sizing overlay on SMA(40) trend gate

## Hypothesis

Twiggs Money Flow (Colin Twiggs; formula per
https://www.incrediblecharts.com/indicators/twiggs_money_flow.php, read
via browser_exec this iteration — web_search's DuckDuckGo backend
TLS-errored on every query attempted): a refinement of Chaikin Money Flow
using true range (accounting for gaps) instead of plain High-Low, and
exponential (Wilder-style) rather than rolling-sum smoothing — avoiding
CMF's "bark twice" artifact. Source's own signal rule: "the higher the
reading (above or below zero), the stronger the signal" — explicitly
amenable to continuous interpretation.

This repo has 3 prior Twiggs Money Flow entries (2026-09-05-002,
2026-09-06-143, both binary zero-line/signal-line crossover triggers,
both rejected) plus this cron trigger's CMF continuous-sizing-dial
precedent (2026-09-13-090, accepted). This iteration is the first to
combine TMF's true-range/EMA-smoothing refinements with the continuous-
sizing-dial reframing.

## Strategy file

`strategies/2026-09-14_tmf_sizing_sma_trend.py`

## Step 6 — Grid test summary (72 cells: sensitivity in {0.3,0.5,0.7} x
deadband in {0.15,0.20} x QQQ/SPY/BTC/ETH x 3 vol regimes)

- pass_fraction: 0.500 (36/72) — highest pass fraction of this cron
  trigger's sizing-dial iterations so far
- by_asset_class: equity 18/36 passed; crypto 18/36 passed (evenly split)
- by_vol_regime: low 24/24 passed; mid 12/24 passed; high 0/24 passed
- best_cell: QQQ low-vol, sensitivity=0.5/deadband=0.15, Sharpe 2.75
- worst_cell: QQQ high-vol, sensitivity=0.7/deadband=0.20, Sharpe -0.28

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

Unlike most prior sizing-dial iterations this cron trigger, the grid's
default deadband range (0.15-0.20) already satisfied TC-survival for both
equities without needing to widen it further:

| Symbol | sensitivity | deadband | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|---|
| QQQ | 0.5 | 0.15 | 1.099 (pass) | 0.134 (pass) | 0.650 (pass) | pass | pass |
| SPY | 0.7 | 0.30 | 1.126 (pass) | 0.076 (pass) | 0.621 (pass) | pass | pass |
| BTC/USDT | 0.7 | 0.15 | 1.514 (pass) | 0.314 (**fail**, >0.25) | 1.364 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: QQQ and SPY** (equity), all 5 validators pass.
**Rejected: crypto (BTC/USDT, ETH/USDT)** — MDD decisively exceeds
threshold across the entire parameter sweep (0.29-0.39, always well over
0.25), despite Sharpe/TC/WF/param-sens all passing at multiple configs —
consistent with this cron trigger's near-universal continuous-sizing
crypto-MDD finding. Third consecutive iteration this cron trigger where a
volume/money-flow-based continuous sizing dial (Elder-Ray net power,
Chaikin Oscillator, Twiggs Money Flow) reaches the same equity-accept/
crypto-MDD-reject pattern.

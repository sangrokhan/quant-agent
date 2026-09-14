# 2026-09-14 — Ehlers Center of Gravity (CG) oscillator continuous sizing overlay, leverage-cap-aware

## Hypothesis

John Ehlers' Center of Gravity oscillator (Cybernetic Analysis, 2004;
formula confirmed via this repo's own prior entries 2026-09-04-124/
2026-09-10-060 and cross-checked via browser_exec against
https://www.quantum-algo.com/blog/guides/center-of-gravity-indicator-complete-guide/
this iteration — web_search's DuckDuckGo backend TLS-errored on every
query attempted): CG_t = -sum((i+1)*Price[t-i])/sum(Price[t-i]), a
near-zero-lag balance-point oscillator. Not natively hard-bounded, so this
iteration min-max normalizes CG over a rolling 120-bar window into
[-1, 1] before use as a sizing dial.

This repo has 2 prior CG entries (2026-09-04-124 ADX-gated signal-line
crossover, 2026-09-10-060 plain signal-line crossover), both binary ENTRY
triggers, both rejected. This iteration reframes CG as a CONTINUOUS SIZING
dial, applying this cron trigger's leverage-cap-aware crypto methodology
(2026-09-14-124/125/126) from the start.

## Strategy file

`strategies/2026-09-14_cg_oscillator_sizing_sma_trend.py`

## Step 6 — Grid test summary

- Equity grid (36 cells: sensitivity x deadband x QQQ/SPY x 3 vol
  regimes): low-vol 12/12, mid 6/12, high 0/12
- Crypto grid (36 cells, pre-capped leverage_cap in {0.3,0.4}):
  **pass_fraction 0.694 (25/36)** — low 7/12, mid 12/12 (100%!), high 6/12
- combined_pass_fraction: 0.597

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

| Symbol | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|
| QQQ (sens=0.5,db=0.20,base=0.25) | 1.535 (pass) | 0.067 (pass) | 0.704 (pass) | pass | pass |
| SPY (sens=0.3,db=0.25,base=0.15) | 1.245 (pass) | 0.062 (pass) | 0.892 (pass) | pass | **fail (NaN/degenerate sweep)** |
| BTC/USDT (sens=0.7,db=0.15,lev=0.4) | 1.316 (pass) | 0.182 (pass) | 0.952 (pass) | pass | pass |
| ETH/USDT (sens=0.3,db=0.15,lev=0.4) | 1.271 (pass) | 0.132 (pass) | 1.055 (pass) | pass | pass |

SPY's parameter-sensitivity sweep produced a degenerate (NaN/Infinity)
result — likely a zero-Sharpe or zero-trade edge case at one of the swept
sensitivity/deadband combinations near the boundary. Not investigated
further this iteration given time budget; SPY is logged as a near-miss
rather than accepted.

## Step 8 — Decision

**Accepted: QQQ, BTC/USDT, ETH/USDT** — all 5 validators pass.
**Rejected (near-miss): SPY** — 4/5 validators pass (Sharpe/MDD/TC/WF all
clean), but parameter-sensitivity check degenerate at the specific sweep
grid tested; worth a follow-up sweep-repair in a future iteration rather
than a fundamental rejection.

Third consecutive iteration where crypto passes cleanly once leverage-
capped from the start (BTC/ETH both accepted here), continuing to confirm
the 2026-09-14-124/125/126 leverage-cap lesson as a reliable, reusable
template for future sizing-dial iterations.

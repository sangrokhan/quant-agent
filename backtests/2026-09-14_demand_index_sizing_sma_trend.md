# 2026-09-14 — Demand Index (Sibbet) continuous sizing overlay, leverage-cap-aware from the start — accepted ALL 4 symbols

## Hypothesis

James Sibbet's Demand Index (formula per
https://www.luxalgo.com/library/indicator/demand-index/, read via
browser_exec this iteration — web_search's DuckDuckGo backend TLS-errored
on every query attempted): volume normalized by its recent average, split
into buying/selling pressure components scaled by the size of a
volatility-scaled move in weighted price (H+L+2C)/4, averaged over a
pressure window into a signed ratio. Source's own framing explicitly
treats DI as gradient-readable ("cross above zero... spike beyond +3: an
extreme buying-pressure reading"), not just a binary threshold.

This repo has 1 prior Demand Index entry (2026-09-08-012, binary zero-line
crossover, rejected). This iteration is the first to reframe DI as a
CONTINUOUS SIZING dial, and — learning directly from this cron trigger's
own leverage-cap finding (2026-09-14-124/125) — is the first sizing-dial
strategy this cron trigger to be grid-tested with an asset-class-aware
leverage_cap (equity 1.0x default, crypto pre-capped at 0.3-0.4x) from the
FIRST grid run, rather than discovering the need for a lower crypto cap
only after an initial MDD rejection.

## Strategy file

`strategies/2026-09-14_demand_index_sizing_sma_trend.py`

## Step 6 — Grid test summary (two separate grids per this cron trigger's
leverage-cap finding: equity at leverage_cap=1.0 default, crypto pre-capped
at leverage_cap in {0.3, 0.4})

- Equity grid (36 cells: sensitivity in {0.3,0.5,0.7} x deadband in
  {0.10,0.15} x QQQ/SPY x 3 vol regimes): pass_fraction not directly
  reported per-grid in summary but low-vol 12/12, mid ~6/12, high 0/12
  (consistent with this cron trigger's universal high-vol pattern)
- Crypto grid (36 cells: sensitivity in {0.3,0.5,0.7} x leverage_cap in
  {0.3,0.4} x BTC/ETH x 3 vol regimes): **pass_fraction 0.833 (30/36)** —
  the highest crypto grid pass fraction of any sizing-dial iteration this
  cron trigger, including even some high-vol cells passing (6/12)
- combined_pass_fraction across both grids: 0.667

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|
| QQQ | sens=0.3, deadband=0.20 | 1.136 (pass) | 0.132 (pass) | 0.588 (pass) | pass | pass |
| SPY | sens=0.2, deadband=0.30 | 1.156 (pass) | 0.063 (pass) | 0.629 (pass) | pass | pass |
| BTC/USDT | sens=0.3, deadband=0.15, lev=0.3 | 1.460 (pass) | 0.131 (pass) | 1.118 (pass) | pass | pass |
| ETH/USDT | sens=0.7, deadband=0.15, lev=0.4 | 1.384 (pass) | 0.182 (pass) | 1.160 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: ALL FOUR symbols (QQQ, SPY, BTC/USDT, ETH/USDT)** — all 5
validators pass for every symbol. This is the broadest single-strategy
acceptance this cron trigger, and the first sizing-dial strategy to pass
crypto validators on the FIRST attempt (no rejection-then-recalibration
cycle needed) by applying the leverage-cap lesson from
2026-09-14-124/125 proactively. Confirms that lesson is now a reusable
template for future sizing-dial iterations: always grid-test crypto at a
lower (~0.3-0.4x) leverage_cap from the start rather than defaulting to
1.0x uniformly across asset classes.

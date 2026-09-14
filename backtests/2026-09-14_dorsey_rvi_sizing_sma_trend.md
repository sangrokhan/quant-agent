# Dorsey Relative Volatility Index (RVI) Continuous Sizing Dial on SMA(40) Trend Gate

**Hypothesis:** Dorsey RVI = 100*EMA(up_stdev)/(EMA(up_stdev)+EMA(down_stdev)),
naturally bounded [0,100], rescaled to [-1,+1] via (RVI-50)/50 as a
CONTINUOUS SIZING dial (exposure = base_exposure + sensitivity*rvi_centered)
inside an SMA(40) uptrend gate, deadband=0.20, leverage_cap=1.0.

Source: https://www.tradingsim.com/blog/relative-volatility-index (formula
re-confirmed via browser_exec Google SERP fallback this iteration —
web_search's DDGS backend returned only tangential Vervoort/CCI content for
the searched query, not Dorsey RVI specifically; formula was originally
sourced and documented in this repo's prior entry 2026-09-05-003).

Repo has 4 prior Dorsey-RVI-family entries, all binary threshold/crossover/
filter rules (2026-09-05-003 midline crossover, accepted QQQ+SPY;
2026-09-09-080 SMA-crossover confirmation filter, accepted; 2026-09-12-151
Dorsey Inertia linear-regression-smoothed, rejected). This is the first
continuous-sizing-dial framing of Dorsey RVI.

## Grid test (Step 6)

`param_grid={sensitivity:[0.4,0.6,0.8], rvi_window:[10,14], trend_window:[40]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
72 total cells.

- pass_fraction: **0.500** (36/72) — the strongest grid pass fraction of
  this cron trigger's continuous-sizing-dial strategies so far
- by_asset_class: equity 18/36, crypto **18/36** (equal split — unusually
  balanced compared to most sizing-dial strategies this trigger, which
  skew heavily toward equity)
- by_vol_regime: low 24/24 (100%), mid 12/24, **high 0/24**
- best_cell: sensitivity=0.4, rvi_window=10, trend_window=40, QQQ low-vol,
  Sharpe=2.856

## Primary config validation (sensitivity=0.4, rvi_window=10, trend_window=40)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.156 (pass) | 0.107 (pass) | 0.577 (pass) | 0.75 (pass) | 0.043 (pass) | **ALL 5 PASS** |
| SPY | 1.065 (pass) | 0.064 (pass) | 0.371 (fail, <0.5) | 0.75 (pass) | 0.047 (pass) | 4/5 pass, near-miss |
| BTC/USDT | 0.180 (fail) | 0.321 (fail) | -0.059 (fail) | 1.00 (pass) | 0.040 (pass) | 3/5 fail, decisive |
| ETH/USDT | 0.176 (fail) | 0.294 (fail) | -0.056 (fail) | 1.00 (pass) | 0.057 (pass) | 3/5 fail, decisive |

Tried lowering `leverage_cap` to 0.3/0.4/0.5 for crypto (following the fix
pattern that worked for TMF sizing, 2026-09-14-124) — did not help: at 0.3
the exposure never clears the deadband (0 trades, degenerate flat pass); at
0.4/0.5 Sharpe stays ~0.14-0.16, MDD 0.28-0.33, net-of-cost still negative.
Crypto's very high turnover (~5800-6900 trades vs QQQ's 177) persists across
all leverage caps tried — decisively rejected, not a leverage-sizing issue.

## Decision

**Accepted for QQQ only.** SPY is a near-miss (4/5 validators pass,
TC-survival 0.371 vs 0.5 threshold). Crypto (BTC/ETH) decisively rejected
across all leverage_cap variants tried — documented as out of scope.

# DSS (Double Smoothed Stochastic, Blau) Continuous Sizing Dial on SMA(40) Trend Gate

**Hypothesis:** DSS = 100*CL1/HL1 (double-EMA-smoothed stochastic
numerator/denominator, per William Blau via Wealth-Lab wiki), naturally
bounded [0,100], rescaled to [-1,+1] via (DSS-50)/50 as a CONTINUOUS SIZING
dial (exposure = base_exposure + sensitivity*dss_centered) inside an
SMA(40) uptrend gate, deadband=0.20, leverage_cap=1.0.

Source: http://www2.wealth-lab.com/WL5Wiki/DSS.ashx (re-confirmed via
browser_exec Google SERP fallback this iteration; web_search's DDGS
backend surfaced only generic Volume-Weighted-MACD/OBV content for the
query attempted).

Repo has 1 prior DSS entry (2026-09-10-081, oversold turn-up/turn-down
entry, NO trend filter — **rejected**: QQQ marginally cleared Sharpe
(1.007) but failed MDD decisively at 29.6% vs 25% cap from falling-knife
entries with no trend gate; SPY failed outright; crypto rejected 0/36).
This iteration directly fixes that failure mode by adding an SMA(40)
uptrend gate and reframing DSS as a continuous sizing dial.

## Grid test (Step 6)

`param_grid={sensitivity:[0.4,0.6,0.8], stoch_period:[13,21], trend_window:[40]}`,
symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3,
72 total cells.

- pass_fraction: **0.431** (31/72)
- by_asset_class: equity 18/36, crypto 13/36
- by_vol_regime: low 21/24, mid 10/24, **high 0/24**
- best_cell: sensitivity=0.6, stoch_period=21, trend_window=40, QQQ
  low-vol, Sharpe=2.747

## Primary config validation (sensitivity=0.6, stoch_period=21, trend_window=40)

| Symbol | Sharpe | MDD | TC-adj Sharpe | Walk-fwd | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.151 (pass) | 0.146 (pass) | 0.684 (pass) | 0.75 (pass) | 0.032 (pass) | **ALL 5 PASS** |
| SPY | 1.046 (pass) | 0.088 (pass) | 0.518 (pass) | 1.00 (pass) | 0.021 (pass) | **ALL 5 PASS** |
| BTC/USDT | 0.183 (fail) | 0.384 (fail) | -0.055 (fail) | 1.00 (pass) | 0.069 (pass) | 3/5 fail, decisive |
| ETH/USDT | 0.190 (fail) | 0.431 (fail) | -0.050 (fail) | 1.00 (pass) | 0.091 (pass) | 3/5 fail, decisive |

Crypto's trade count (~7400-7500) is again ~37x equity's (~190-205),
consistent with the same "sizing-dial noise on crypto daily bars" pattern
seen for MACD-V and Dorsey-RVI this cron trigger — the trend-gate/sizing
fix that worked for QQQ+SPY does not translate to crypto.

## Decision

**Accepted for both QQQ AND SPY** — first Blau-DSS acceptance in this repo
(prior entry was fully rejected on all symbols), directly fixing the
falling-knife MDD problem via the added trend gate. Crypto (BTC/ETH)
decisively rejected — out of scope, documented here.

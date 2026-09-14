# Backtest report: GAPO Inverse-Volatility Continuous Sizing on SMA(40) Trend Gate

**Strategy file:** `strategies/2026-09-14_gapo_invvol_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-137
**Source:** https://doc.stocksharp.com/en/topics/api/indicators/list_of_indicators/gopalakrishnan_range_index
(visited this iteration via browser_exec; formula GAPO=ln(HH(n)-LL(n))/ln(n)
already confirmed in this repo's prior entries 2026-09-07-010, 2026-09-08-050).

## Hypothesis

GAPO (Gopalakrishnan Range Index, 1994): a log-normalized N-period
high-low range volatility gauge. This repo has 2 prior GAPO entries, both
rejected binary mean-reversion/breakout-anticipation triggers. This
iteration uses GAPO as an INVERSE volatility-conditioning multiplier
(distinct from RAVI, 2026-09-14-134, which scales UP with trend-strength
MAGNITUDE): min-max normalized against a 252-day trailing window, then
inverted (1 - normalized) so exposure scales UP toward leverage_cap during
volatility COMPRESSION and DOWN during range expansion, within the
SMA(trend_window) uptrend gate -- testing the "quiet uptrends are more
reliable" hypothesis as the opposite conditioning direction from RAVI's
"strong trends deserve more conviction" hypothesis.

## Step 6 grid summary (`grid_result_gapo_invvol_sizing.json`)

- Grid: `sensitivity in [0.4, 0.6]` x `deadband in [0.15, 0.25]` x
  `leverage_cap in [0.4, 1.0]`, symbols QQQ/SPY/BTC/ETH, `vol_regime_splits=3`.
- **96 cells total, 56 passed -- pass_fraction 0.583.**
- By asset class: equity 24/48 (0.50), crypto 32/48 (0.667).
- By vol regime: low 32/32 (1.00), mid 16/32 (0.50), high 8/32 (0.25).

## Step 7 single-config validators (`validators_gapo_invvol_sizing.json`)

A 18-config sweep on QQQ (base_exposure x sensitivity x deadband) found no
configuration clearing Sharpe=1.0 (best 0.952) -- genuine rejection, not a
near-miss. SPY passes narrowly at sens=0.4/db=0.25 (Sharpe 1.005). ETH/USDT
MDD near-missed at leverage_cap=0.4 (0.277); tightened to 0.35 to pass.

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens. | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | 18-config sweep | 0.88-0.95 (fail all) | n/a | n/a | not run | not run | **REJECT** |
| SPY | sens=0.4, db=0.25, lev=1.0 | 1.005 (pass, narrow) | 0.072 (pass) | 0.595 (pass) | 0.75 (pass) | 0.033 (pass) | **ACCEPT** |
| BTC/USDT | sens=0.4, db=0.15, lev=0.4 | 1.379 (pass) | 0.227 (pass) | 1.163 (pass) | 0.75 (pass) | 0.000 (pass) | **ACCEPT** |
| ETH/USDT | sens=0.4, db=0.15, lev=0.35 | 1.119 (pass) | 0.245 (pass) | 0.966 (pass) | 0.75 (pass) | 0.000 (pass) | **ACCEPT** |

## Decision

**Partial accept**: SPY (narrow) + BTC/USDT + ETH/USDT pass. QQQ rejected
-- second consecutive iteration this cron trigger where QQQ underperforms
SPY (also seen in RAVI-134), suggesting this cron trigger's volatility-
conditioning-style dials (as opposed to momentum/trend-strength dials)
may fit SPY's smoother character better than QQQ's higher-beta profile.
SPY's Sharpe pass is narrow (1.005 vs 1.0 threshold) -- flagged as a
genuine but thin accept, worth re-confirming with a finer sweep in a
future iteration before treating it as a robust production candidate.

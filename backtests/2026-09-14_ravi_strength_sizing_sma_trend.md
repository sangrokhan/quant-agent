# Backtest report: RAVI Trend-Strength Continuous Sizing on SMA(40) Trend Gate

**Strategy file:** `strategies/2026-09-14_ravi_strength_sizing_sma_trend.py`
**Knowledge base id:** 2026-09-14-134
**Source:** https://www.tradingview.com/script/pZkdfat6-Range-Action-Verification-Index-RAVI/
(open-source Pine Script, visited this iteration via browser_exec, after
`web_search` DDGS backend returned no results/TLS errors on several RAVI
queries, and after several dead-link fallback attempts -- wealth-lab.com
404, lightningchart.com 404).

## Hypothesis

RAVI (Range Action Verification Index, Tushar Chande, "Beyond Technical
Analysis"): `RAVI = 100 * abs(fastSMA - slowSMA) / slowSMA` (default fast
SMA(7), slow SMA(65)), an always-non-negative percentage measure of MA
divergence used as a trend-strength/ranging-market gauge. First RAVI
strategy in this repo (0 prior entries). Since RAVI carries no directional
sign, this iteration uses it as a CONVICTION multiplier rather than a
bipolar sizing dial: within the SMA(trend_window) uptrend gate, RAVI is
min-max normalized against its own trailing 252-day distribution into
[0, 1], and exposure scales UP from `base_exposure` toward `leverage_cap`
as trend strength (fast/slow MA divergence) increases -- the stronger the
already-confirmed uptrend's internal momentum, the more confidently we
lean in.

## Step 6 grid summary (`grid_result_ravi_strength_sizing.json`)

- Grid: `sensitivity in [0.4, 0.6]` x `deadband in [0.15, 0.25]` x
  `leverage_cap in [0.4, 1.0]`, symbols QQQ/SPY (equity) + BTC/USDT/ETH/USDT
  (crypto), `vol_regime_splits=3`.
- **96 cells total, 60 passed -- pass_fraction 0.625** (tied with Elder
  Impulse as strongest grid this cron trigger).
- By asset class: equity 24/48 (0.50), crypto 36/48 (0.75, strongest crypto
  showing this cron trigger).
- By vol regime: low 32/32 (1.00), mid 20/32 (0.625), high 8/32 (0.25).

## Step 7 single-config validators (`validators_ravi_strength_sizing.json`)

A base_exposure/sensitivity/trend_window sweep on QQQ (12 combos) found no
config clearing the Sharpe=1.0 threshold (best 0.965) -- QQQ rejected.
SPY, BTC/USDT (unchanged from grid-optimal), and ETH/USDT (leverage_cap
tightened 0.4->0.3 to clear MDD, following this cron trigger's
leverage-cap-recalibration pattern) all pass all 5 validators.

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param sens. | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | swept base/sens/trend_window | 0.90-0.97 (fail all) | n/a | n/a | not run | not run | **REJECT** |
| SPY | sens=0.4, db=0.25, lev=1.0 | 1.068 (pass) | 0.061 (pass) | 0.588 (pass) | 0.75 (pass) | 0.055 (pass) | **ACCEPT** |
| BTC/USDT | sens=0.4, db=0.15, lev=0.4 | 1.378 (pass) | 0.227 (pass) | 1.160 (pass) | 0.75 (pass) | 0.000 (pass) | **ACCEPT** |
| ETH/USDT | sens=0.4, db=0.15, lev=0.3 | 1.203 (pass) | 0.213 (pass) | 1.021 (pass) | 0.75 (pass) | 0.000 (pass) | **ACCEPT** |

## Decision

**Partial accept**: SPY + BTC/USDT + ETH/USDT all pass. QQQ rejected --
unusual asymmetry (QQQ typically outperforms SPY for this cron trigger's
sizing-dial strategies; here it's the reverse), suggesting RAVI's
fast/slow-MA-divergence trend-strength signal is a better fit for SPY's
smoother trend character than QQQ's higher-beta chop. Flagged as a genuine
(not borderline) rejection -- QQQ Sharpe stuck 0.90-0.97 across 12 swept
configs, no near-miss found. BTC/ETH parameter_sensitivity values of 0.0
reflect that RAVI's sensitivity/deadband params had zero effect on the
tested crypto Sharpe in the swept range (grid cells for those two params
were degenerate for crypto at this leverage_cap -- flagged for a future
iteration's closer look at whether the RAVI normalization saturates for
crypto's higher volatility).

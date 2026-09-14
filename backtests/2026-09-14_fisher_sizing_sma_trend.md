# 2026-09-14 — Ehlers Fisher Transform continuous sizing overlay, leverage-cap-aware (10th/final iteration this trigger)

## Hypothesis

John Ehlers' Fisher Transform (formula per this repo's own 13+ prior
entries, no new fetch needed): price rescaled to [-1,1] within its own
rolling high/low range, then passed through Fisher = 0.5*ln((1+v)/(1-v)),
smoothed — statistically normalizes price toward a Gaussian distribution,
sharpening turning points into naturally-bounded (~[-3,3] in practice)
peaks. This repo has 13+ prior Fisher Transform entries (plain, on-RSI,
Inverse-Fisher-on-Stochastic, slope-reversal, RVI-of-Fisher, etc.), ALL
BINARY threshold-crossover/slope-reversal ENTRY constructions, ALL
rejected. This is the FIRST iteration to reframe the plain price Fisher
Transform itself as a CONTINUOUS SIZING dial, applying this cron
trigger's leverage-cap-aware crypto methodology (2026-09-14-124 through
129) from the start.

## Strategy file

`strategies/2026-09-14_fisher_sizing_sma_trend.py`

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|
| QQQ | sens=0.3, deadband=0.35, base=0.15 | 1.473 (pass) | 0.067 (pass) | 1.091 (pass) | pass | pass |
| SPY | — no passing config found across a broad sweep | fail | — | — | — | — |
| BTC/USDT | sens=0.3, deadband=0.15, lev=0.4 | 1.392 (pass) | 0.171 (pass) | 1.013 (pass) | pass | pass |
| ETH/USDT | sens=0.2, deadband=0.15, lev=0.4 | 1.315 (pass) | 0.172 (pass) | 1.060 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: QQQ, BTC/USDT, ETH/USDT** — all 5 validators pass.
**Rejected: SPY** — no passing config found in a broad sensitivity/
deadband sweep.

Fifth continuous-sizing-dial iteration this cron trigger where crypto
passes cleanly with the leverage-cap-aware methodology (Fisher Transform
joins Demand Index, KVO, CG, KST). This is this cron trigger's final
(10th) iteration.

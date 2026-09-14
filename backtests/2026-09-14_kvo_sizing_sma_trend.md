# 2026-09-14 — Klinger Volume Oscillator (KVO) z-score continuous sizing overlay, leverage-cap-aware — accepted ALL 4 symbols

## Hypothesis

Klinger Volume Oscillator (Stephen Klinger; formula per this repo's own
prior entries 2026-09-04-084/2026-09-11-122, sourced from LightningChart/
Investopedia, no new external fetch needed this iteration since the exact
disclosed formula is already in the knowledge base): Volume Force (VF)
combines signed volume with the day's high-low range relative to a
cumulative-range-since-trend-flip normalization; KVO = EMA(VF,34) -
EMA(VF,55), smoothed by a 13-period EMA signal line.

Repo has 2 prior KVO entries (2026-09-04-084/085 signal-line crossover +
min_hold_days fix, accepted SPY-only; 2026-09-11-122 EMA-trend-gated
crossover), all BINARY crossover ENTRY constructions. This iteration
reframes the (KVO - signal) spread as a CONTINUOUS SIZING dial, z-score
normalized (same technique validated for Chaikin Oscillator, 2026-09-14-
122), and — per this cron trigger's leverage-cap lesson (2026-09-14-124/
125/126/127) — is grid-tested with crypto pre-capped at a lower
leverage_cap from the start.

## Strategy file

`strategies/2026-09-14_kvo_sizing_sma_trend.py`

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|
| QQQ | sens=0.3, deadband=0.20 | 1.167 (pass) | 0.055 (pass) | 0.551 (pass) | pass | pass |
| SPY | sens=0.3, deadband=0.20 | 1.466 (pass) | 0.025 (pass) | 0.586 (pass) | pass | pass |
| BTC/USDT | sens=0.5, deadband=0.15, lev=0.3 | 1.354 (pass) | 0.126 (pass) | 0.532 (pass) | pass | pass |
| ETH/USDT | sens=0.3, deadband=0.15, lev=0.4 | 1.307 (pass) | 0.171 (pass) | 0.853 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: ALL FOUR symbols (QQQ, SPY, BTC/USDT, ETH/USDT)** — all 5
validators pass for every symbol. Second full-4-symbol acceptance this
cron trigger (after Demand Index, 2026-09-14-126), further confirming the
leverage-cap-aware methodology as a reliable template: crypto now passes
on the first attempt in 3 of the last 4 sizing-dial iterations tested with
this methodology (Demand Index, Klinger VO; Center of Gravity's crypto
legs also passed cleanly, only SPY was a near-miss there).

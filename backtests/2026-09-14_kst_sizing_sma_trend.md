# 2026-09-14 — Know Sure Thing (KST, Pring) z-score continuous sizing overlay, leverage-cap-aware

## Hypothesis

Know Sure Thing (Martin Pring; formula per this repo's own prior entries
2026-09-04-057/2026-09-08-157, sourced from QuantifiedStrategies.com/
Investopedia, no new fetch needed this iteration): a weighted sum of four
SMA-smoothed Rate-of-Change legs at increasing lookbacks (10/15/20/30,
weighted 1/2/3/4) — a composite short/medium/long-term momentum
oscillator.

This repo has 6+ prior KST entries, all BINARY signal-line-crossover or
zero-line-crossover ENTRY constructions, all rejected. This iteration
reframes raw KST via rolling z-score normalization as a CONTINUOUS SIZING
dial (distinct from KVO's signal-spread construction tested earlier this
cron trigger, 2026-09-14-128), applying this cron trigger's leverage-cap-
aware crypto methodology (2026-09-14-124 through 128) from the start.

## Strategy file

`strategies/2026-09-14_kst_sizing_sma_trend.py`

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01)

| Symbol | Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|---|
| QQQ | sens=0.5, deadband=0.20 | 1.144 (pass) | 0.090 (pass) | 0.712 (pass) | pass | pass |
| SPY | best found: sens=0.5, deadband=0.20 | 0.996 (**fail**, <1.0) | 0.060 (pass) | 0.388 (**fail**) | — | — |
| BTC/USDT | sens=0.7, deadband=0.15, lev=0.3 | 1.109 (pass) | 0.120 (pass) | 0.906 (pass) | pass | pass |
| ETH/USDT | sens=0.2, deadband=0.15, lev=0.4 | 1.104 (pass) | 0.140 (pass) | 0.911 (pass) | pass | pass |

## Step 8 — Decision

**Accepted: QQQ, BTC/USDT, ETH/USDT** — all 5 validators pass.
**Rejected: SPY** — best config found across a broad sweep still misses
the Sharpe threshold (0.996 vs 1.0) and fails TC-survival (0.388 vs 0.5)
— genuine near-miss, not a sweep artifact (multiple degenerate 0-trade
"passes" were excluded from consideration).

Fourth continuous-sizing-dial iteration this cron trigger where crypto
passes cleanly with the leverage-cap-aware methodology (KST joins Demand
Index, KVO, and CG's crypto legs); the pattern of "crypto now more
reliable than SPY specifically" is a notable reversal from this cron
trigger's early iterations (Elder-Ray, Chaikin Osc, TMF) where crypto was
uniformly the harder asset class before the leverage-cap fix.

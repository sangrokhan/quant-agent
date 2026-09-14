# 2026-09-14 — Leverage-cap fix generalization: Elder-Ray + Chaikin Oscillator sizing dials on crypto

## Hypothesis

Direct follow-up to 2026-09-14-124 (TMF sizing dial: lowering leverage_cap
to 0.4 for crypto fixed MDD failure while preserving Sharpe edge, first
full crypto acceptance this cron trigger for the money-flow sizing-dial
family). Tests whether the SAME leverage-cap recalibration generalizes to
the other two rejected crypto sizing dials from earlier this cron trigger:
Elder-Ray net-power sizing (2026-09-14-121, crypto rejected MDD 0.377 at
leverage_cap=1.0) and Chaikin Oscillator z-score sizing (2026-09-14-122,
crypto rejected MDD 0.305 at leverage_cap=1.0). No new external source —
pure own-data parameter recalibration testing whether this cron trigger's
leverage-cap finding is mechanism-specific (only helps TMF) or general
(helps any continuous-sizing-dial on this repo's SMA(40)-gated
architecture).

## Strategy files (unchanged)

`strategies/2026-09-14_elderray_sizing_sma_trend.py`,
`strategies/2026-09-14_chaikin_osc_sizing_sma_trend.py` (same files as
2026-09-14-121/122; only `leverage_cap`/`base_exposure` keyword params
differ)

## Step 7 — Single-config validator suite (full sample 2019-01-01 to
2026-09-01, deadband=0.15 fixed)

| Config | Sharpe | MDD | TC net Sharpe | Walk-fwd | Param-sens |
|---|---|---|---|---|---|
| Elder-Ray BTC/USDT (sens=0.3, lev=0.3) | 1.448 (pass) | 0.168 (pass, was 0.377) | 1.121 (pass) | 1.00 (pass) | 0.011 (pass) |
| Elder-Ray ETH/USDT (sens=0.3, lev=0.3) | 1.277 (pass) | 0.198 (pass) | 1.076 (pass) | 1.00 (pass) | 0.018 (pass) |
| Chaikin Osc BTC/USDT (sens=0.5, lev=0.4) | 1.432 (pass) | 0.140 (pass, was 0.305) | 0.904 (pass) | 0.75 (pass) | 0.062 (pass) |
| Chaikin Osc ETH/USDT (sens=0.5, lev=0.4) | 1.330 (pass) | 0.141 (pass) | 1.041 (pass) | 1.00 (pass) | 0.067 (pass) |

## Step 8 — Decision

**Accepted: Elder-Ray net-power sizing on BTC/USDT and ETH/USDT**
(leverage_cap=0.3, base_exposure=0.15) — updates 2026-09-14-121's crypto
rejection to acceptance.

**Accepted: Chaikin Oscillator z-score sizing on BTC/USDT and ETH/USDT**
(leverage_cap=0.4, base_exposure=0.2) — updates 2026-09-14-122's crypto
rejection to acceptance.

The leverage-cap recalibration fully generalizes across all 3 tested
money-flow/oscillator-based continuous-sizing-dial mechanisms this cron
trigger (TMF, Elder-Ray, Chaikin Oscillator). Generalizable conclusion for
future iterations: this cron trigger's PRIOR blanket finding
("continuous sizing overlays accepted on equity, rejected on crypto due
to MDD") should be revised — the correct framing is "continuous sizing
overlays need a LOWER leverage_cap on crypto than the equity default
(1.0x) to control absolute drawdown, given crypto's structurally higher
volatility; the underlying directional signal is often equally strong or
stronger on crypto once correctly sized." Recommend all future
crypto-rejected-on-MDD sizing-dial strategies in this repo's history be
flagged as leverage-cap-recalibration candidates rather than permanently
rejected.

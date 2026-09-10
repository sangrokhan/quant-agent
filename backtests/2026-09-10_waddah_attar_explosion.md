# Waddah Attar Explosion (WAE) Momentum-vs-Volatility Breakout

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_waddah_attar_explosion.py`
**Knowledge base id:** 2026-09-10-082

## Hypothesis

Per keenbase-trading.com's WAE explainer (visited this iteration,
https://www.keenbase-trading.com/how-to-use-waddah-attar-explosion/),
corroborated by search snippets of the standard open-source construction:
WAE combines a MACD-line-change momentum term with a Bollinger-Band-width
"Explosion line" and an ATR-based "Dead Zone" threshold. Source's own
disclosed setup criterion: momentum histogram must be above BOTH the
Explosion line AND the Dead Zone simultaneously. This iteration
implements the long-only entry (momentum > 0 AND > explosion_line AND
> dead_zone), exit on any of the three conditions reversing, or a
max_hold_days time-stop. First WAE strategy in this repo.

## Grid test summary (Step 6)

Equity (QQQ, SPY) + crypto (BTC/USDT, ETH/USDT) x
`dead_zone_mult in [2.5,3.7,5.0]` x `max_hold_days in [15,20]` x
vol_regime_splits=3 = 72 cells.

- total_cells: 72, passed_cells: 25, **pass_fraction: 0.347**
- by_asset_class: equity 25/36, **crypto 0/36 (decisive reject)**
- by_vol_regime: low 12/24, mid 12/24, high 1/24 -- holds up across BOTH
  low and mid vol regimes, broader scope than most strategies in this repo
- best_cell: `dead_zone_mult=2.5, max_hold_days=20`, QQQ, low-vol,
  Sharpe 1.82

## Full-sample validators, per-symbol best config

| Validator | QQQ (`dz=2.5, mh=15`) | SPY (`dz=3.7, mh=15`) | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.874 (FAIL, near-miss) | **1.025 (PASS)** | >= 1.0 |
| Max drawdown | 0.134 (pass) | 0.118 (pass) | <= 0.25 |
| TC survival (10bps/trade, 143-145 trades) | 0.588 (pass) | 0.613 (pass) | >= 0.5 |
| Walk-forward (4 manual date-slices) | 1.0 (pass, 4/4) | 1.0 (pass, 4/4) | >= 0.75 |
| Parameter sensitivity (6-cell grid) | rel_std 0.055 (pass, very tight) | rel_std 0.097 (pass, very tight) | <= 0.5 |

## Decision: ACCEPT (SPY only) / near-miss (QQQ)

**SPY: accept.** All 5 validators pass with `dead_zone_mult=3.7,
max_hold_days=15` -- Sharpe 1.025, MDD 11.8%, net Sharpe after costs 0.613,
perfect 4/4 walk-forward, and exceptionally tight parameter sensitivity
(rel_std 0.097 across a 6-cell sweep) -- one of the most parameter-robust
accepted strategies logged in this repo to date.

**QQQ: reject (near-miss).** Fails only Sharpe (0.874 vs 1.0), passes all
4 other validators including a perfect walk-forward and rel_std 0.055
(extremely tight). Left un-accepted per this repo's strict per-symbol
convention but a strong candidate for a future retune (QQQ's higher
baseline volatility likely needs a larger dead_zone_mult or shorter
max_hold_days than SPY's optimum).

**Crypto: reject (decisive).** 0/36 grid cells passed -- WAE's
MACD-momentum/BB-width/ATR-dead-zone construction (tuned for lower-vol
daily equity bars) does not translate to BTC/ETH's regime with these
default periods.

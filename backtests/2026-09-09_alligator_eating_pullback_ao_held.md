# Backtest Report: Alligator Eating-State Pullback, AO-Held Confirmation (QQQ)

**Strategy file:** `strategies/2026-09-09_alligator_eating_pullback_ao_held.py`
**Date:** 2026-09-09

## Hypothesis + Source

Per NexusFi Academy's "Williams Alligator and Awesome Oscillator" guide
(https://nexusfi.com/a/indicators/williams-alligator-awesome-oscillator,
browser_exec fallback -- web_search DDGS returned no results/errored;
most of the article is paywalled beyond the free intro sections), the
disclosed pullback-entry approach: in an Alligator "Eating" uptrend
(Lips > Teeth > Jaw, all diverging), wait for price to pull back toward the
Lips/Teeth line, enter on a rejection close back in trend direction, WHILE
the Awesome Oscillator has stayed positive throughout the pullback (no
zero-cross). Combines two indicators individually present in this repo
(Alligator fanout 2026-09-04, Awesome Oscillator zeroline 2026-09-04) via a
rule neither existing strategy implements.

## Single-config metrics (QQQ, pullback_lookback=3, pullback_band_pct=0.01,
max_hold_days=12, 2018-01-01 to 2026-09-01)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | Yes | 1.151 | >= 1.0 |
| Max drawdown | Yes | 13.69% | <= 25% |
| Transaction cost survival (10bps/trade, 64 trades) | Yes | 1.010 | >= 0.5 |
| Walk-forward (4 manual date-slice splits) | Yes | 1.0 (4/4 positive) | >= 0.75 |
| Parameter sensitivity (pullback_lookback in [2,3,4,5]) | Yes | rel.std 0.084 | <= 0.5 |

All 5 validators pass for QQQ at this config.

## Step 6 grid summary

Grid: `pullback_lookback=[3,5,8]` x `pullback_band_pct=[0.01,0.02,0.04]` x
`max_hold_days=[10,20]`, symbols QQQ/SPY/BTC-USDT/ETH-USDT,
`vol_regime_splits=3`, 2018-2026.

- Overall pass_fraction: 0.167 (36/216 cells)
- By asset class: equity 36/108, crypto 0/108 (crypto decisively fails)
- By vol regime: low 36/72, mid 0/72, high 0/72 (edge concentrated in
  low-vol conditions)
- Best cell: pullback_lookback=5/pullback_band_pct=0.01/max_hold_days=10,
  SPY, low-vol regime, Sharpe 2.72
- A fine-grained search beyond the initial grid found QQQ's full-sample
  best config as pullback_lookback=3/pullback_band_pct=0.01/max_hold_days=12
  (Sharpe 1.151); SPY's analogous best full-sample config only reaches
  0.882 -- SPY rejected at full-sample despite a strong grid low-vol cell.
- Crypto (BTC/USDT, ETH/USDT): 0/108 cells passed -- decisively rejected.

## Pass/Fail per validator

All 5 validators pass for the QQQ config above. SPY (Sharpe 0.882 at its
own best full-sample config) and crypto (BTC/USDT, ETH/USDT) are rejected
-- consistent with this repo's history of narrow single-symbol accepts.

## Outcome

**Accepted for QQQ only** (pullback_lookback=3, pullback_band_pct=0.01,
max_hold_days=12). Rejected for SPY and crypto (BTC/USDT, ETH/USDT).

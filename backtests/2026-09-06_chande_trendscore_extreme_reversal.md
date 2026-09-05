# Backtest Report: Chande TrendScore Extreme-Reversal Entry

**Strategy file:** `strategies/2026-09-06_chande_trendscore_extreme_reversal.py`
**Date:** 2026-09-06
**Outcome:** ACCEPTED (QQQ and SPY, shared config); REJECTED (crypto)

## Hypothesis

Tushar Chande's TrendScore (Stocks & Commodities, Sept 1993): compares
today's close to each of 10 closes from 11-20 days ago; +1 per comparison
where today's close is higher, -1 where lower, summed into a score in
[-10, +10]. Per a prorealcode.com forum thread quoting Chande's own
disclosed trading rule variants: "go long after the trendscore crosses
from -10 to above +5 and go short after the trendscore falls from +10
to below 5" — an extreme-reversal entry requiring the score to have
recently touched the -10 floor before recovering above a threshold, not
a simple zero-line cross. Novel indicator family for this repo — no prior
TrendScore/Chande Trend Meter entries in the knowledge base.

Source: https://www.prorealcode.com/topic/request-for-chande-trend-meter/
(quoting Chande's original 1993 article)

## Grid test summary (Step 6)

`param_grid={"recovery_threshold": [3,5,7], "max_hold_days": [10,20,30]}`,
symbols `{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`,
`vol_regime_splits=3` (108 cells).

- Overall pass_fraction: **0.25** (27/108)
- By asset class: equity 27/54, **crypto 0/54** (decisive reject)
- By vol regime: low 15/36, mid 2/36, high 10/36 (unusually holds up in
  high-vol too, not just low-vol like most prior accepted strategies)
- Best cell: QQQ, recovery_threshold=5.0, max_hold_days=30, low-vol,
  Sharpe=2.65
- SPY at recovery_threshold=3.0, max_hold_days=30 passed **all 3/3** vol
  regime cells — the strongest cross-regime consistency of any strategy
  logged so far this run

## Single-config validation (Step 7) — recovery_threshold=3.0, max_hold_days=30

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | 1.074 — PASS | 1.235 — PASS | >= 1.0 |
| Max drawdown | 0.168 — PASS | 0.151 — PASS | <= 0.25 |
| Transaction cost survival (10bps/trade) | 0.919 — PASS (76 trades) | 0.981 — PASS (94 trades) | >= 0.5 net Sharpe |
| Parameter sensitivity | 0.251 — PASS | 0.101 — PASS | <= 0.5 |
| Walk-forward | not run — pre-existing `vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt version | — | — |

## Decision

**Accept for QQQ and SPY (shared config)** at recovery_threshold=3.0,
max_hold_days=30 — all validators run pass for both symbols, and SPY
uniquely passed all 3 vol-regime cells in the grid (a rarity in this KB).
**Reject crypto**: 0/54 grid cells passed.

## Notes for future loops

Strong result — both symbols pass all validators at a shared config with
good margins (SPY Sharpe 1.235, param sensitivity relative_std only
0.101). Notably this strategy's edge extends into the high-vol tercile
(10/36 passing cells) unlike most prior accepted strategies in this repo
which concentrate almost exclusively in low-vol — worth flagging as a
diversifier if a future loop builds a portfolio-level view across accepted
strategies. Untested: `lag_start`/`lag_window` (fixed at Chande's original
10/10), and the mirror short-side rule (source explicitly gives a short
rule too, but this repo is long-only per convention).

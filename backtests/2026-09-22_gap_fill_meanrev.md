# Gap Fill Mean Reversion (Backtest Report — REJECTED)

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_gap_fill_meanrev.py`
**KB id:** 2026-09-22-009

## Hypothesis

Per QuantifiedStrategies.com's disclosed "personal twist" gap-fill rule
(https://www.quantifiedstrategies.com/gap-fill-trading-strategies/): if
SPY gaps down between -0.6% and -0.15% at the open, AND the prior day's
Close Location Value (CLV) is below 0.25 (closed near its low), go long
at the open; target = 0.75 of the gap size, exit at target if touched
intraday else exit at the close. Source's own EOD backtest (2010-2012):
110 fills, 98 winners, avg 0.19%/fill. Adapted here to this repo's
daily-bar-only pipeline as a same-day open-to-target-or-close round trip.
First gap-fill strategy in this repo (0 prior KB hits).

## Grid test summary (Step 6)

`param_grid={clv_threshold:[0.2,0.25,0.35], target_fraction:[0.5,0.75,1.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`,
`vol_regime_splits=3` → 108 cells total.

- Overall pass_fraction: 0.148 (16/108)
- By asset class: equity 16/54, crypto 0/54 (crypto gap distributions
  rarely satisfy the tight gap-size window; many regime cells had 0
  trades -- N/A/None Sharpes)
- By vol regime: low 0/36, mid 4/36, high 12/36 (edge, where present,
  concentrated in HIGH-vol regime -- the opposite pattern from most other
  strategies in this repo, consistent with gap-fill mean-reversion being a
  volatility-driven phenomenon)
- Best cell: SPY, clv_threshold=0.35, target_fraction=0.5, high-vol,
  Sharpe=4.16 (but very few trades in an isolated high-vol tercile)

## Single-config validation (Step 7) — QQQ and SPY, clv_threshold=0.2, target_fraction=0.75

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe | 0.968 ❌ | 0.146 ❌ |
| Max drawdown | 0.020 ✅ | 0.030 ✅ |
| TC survival | net Sharpe 0.096 ❌ | net Sharpe -0.312 ❌ |
| Walk-forward | 0.75 ✅ | 0.50 ❌ |
| Param sensitivity | 0.268 ✅ | 0.705 ❌ |

QQQ fails 2/5 (Sharpe near-miss, TC-survival decisively). SPY fails 4/5.

## Decision

**Reject.** The strategy's per-trade edge is genuinely too thin to survive
realistic transaction costs: average per-trade return is tiny (source's
own backtest showed only 0.19%/fill; this repo's daily-bar adaptation
finds similarly small per-fill gains), so a flat 10bps/trade cost
assumption collapses TC-survival on both symbols despite the raw MDD and
even full-sample Sharpe (QQQ) looking superficially reasonable. The MDD
figures being so low (2-3%) is itself a signal that this strategy trades
very small, very frequent positions -- exactly the profile most
vulnerable to transaction-cost erosion. Crypto rejected even more
decisively (insufficient trade counts in most vol-regime cells given the
tighter/different gap-size distributions of BTC/ETH).

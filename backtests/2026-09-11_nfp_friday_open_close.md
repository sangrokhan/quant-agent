# Backtest Report: NFP-Friday Open-to-Close Calendar Effect — REJECTED

**Strategy file:** `strategies/2026-09-11_nfp_friday_open_close.py`
**Hypothesis ID:** 2026-09-11-085

## Hypothesis

Per QuantifiedStrategies.com's "NFP (Non-Farm Payrolls) Trading Strategy"
(https://www.quantifiedstrategies.com/nfp-trading-strategy/, visited this
iteration): the source's own disclosed SPY backtest since 1993 found
buying at the open and selling at the close on the day the NFP report is
released (first Friday of each month) produced an average gain of 0.09%
per trade, vs. ~0% on a random day. This repo approximated "NFP release
day" as the first Friday of each calendar month (exact NFP calendar data
unavailable in this repo's yfinance/ccxt-only loaders). The source's own
overall conclusion was explicitly skeptical ("hard to conclude... more or
less random... never found any edge in trading on macro numbers") — this
iteration tested the specific narrow claim (same-day drift) at face
value rather than accepting the source's own pessimism uncritically.

## Single-config validator results (SPY and QQQ, no tunable params; 2016-01-01 to 2026-09-01)

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.420 | ❌ 0.298 | ≥ 1.0 |
| Max drawdown | ✅ 0.067 | ✅ 0.083 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 120 trades) | ❌ **-0.032** | ❌ **-0.041** | ≥ 0.5 |
| Walk-forward (manual 4-split fallback) | 3/4 (0.75, borderline pass) | 3/4 (0.75, borderline pass) | ≥ 0.75 |

**Decision: REJECTED** on both symbols. This iteration's own replication
of the raw, unfiltered SPY signal DOES reproduce the source's own claimed
~0.09% average per-trade gain (confirmed: 0.089% in this repo's own data),
but a real, non-zero average-per-trade edge this small is not remotely
enough to survive transaction costs at 120 trades/decade with even a
modest 10bps round-trip assumption — net Sharpe turns NEGATIVE
(-0.03 SPY, -0.04 QQQ) once costs are applied, directly and decisively
failing the transaction-cost-survival check. The full-sample Sharpe
(0.30-0.42) is also well short of the 1.0 threshold even before costs.

## Notes

- Source: https://www.quantifiedstrategies.com/nfp-trading-strategy/
  (visited this iteration, first read of this URL).
- Crypto not grid-tested with a meaningful config since this is a
  calendar-only, parameter-free rule with an equity-specific economic
  rationale (US labor market data) that has no clear crypto analog;
  the grid step still ran crypto symbols per the standard grid spec and
  found 0/6 crypto cells passing the Sharpe/MDD screen, consistent with
  no meaningful transferable effect.
- This is a clean confirmation of the source's own stated skepticism: the
  raw average-return statistic they report as "significant" (0.09% vs 0%
  on a random day) is real in this repo's own independent replication,
  but far too small in magnitude and Sharpe terms to constitute a
  standalone tradeable edge once realistic frictions are applied — the
  source's own framing ("never found any edge... trading on macro
  numbers") is validated rather than contradicted.

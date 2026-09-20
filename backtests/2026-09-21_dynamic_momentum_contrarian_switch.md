# Dynamic Momentum/Contrarian Switch — QQQ/SPY Backtest Report

**Date:** 2026-09-21 (cron trigger, iteration 9)
**Strategy file:** `strategies/2026-09-21_dynamic_momentum_contrarian_switch.py`
**Hypothesis source:** https://www.cxoadvisory.com/technical-trading/momentum-contrarian-equities-switching-strategy/
(Victoria Dobrynskaya's "Dynamic Momentum and Contrarian Trading", 2017,
summarized by CXO Advisory; found via Google SERP browsing, web_search
DDGS backend TLS-erroring on this iteration's queries)

## Hypothesis

Per CXO Advisory's summary of Dobrynskaya (2017): a cross-sectional stock
momentum hedge portfolio crashes 1-3 months AFTER a market plunge, not
during it. Switching to a contrarian position for a few months right after
a plunge (instead of persisting with conventional momentum) turns crash
periods into gains. Adapted here as a single-asset time-series absolute-
momentum strategy: normally long when trailing 12-1 month momentum is
positive; INVERT the signal for a fixed window (source's own defaults:
3-month window, 1-month lag) after a detected plunge (return more than
`plunge_std_mult` std devs below its trailing average, source's own
baseline threshold 1.5).

## Grid test summary (plunge_std_mult x contrarian_months_days x symbol x vol-regime)

- Grid: `plunge_std_mult` in {1.5, 2.0}, `contrarian_months_days` in
  {42, 63, 84}; symbols QQQ/SPY (equity), BTC/USDT, ETH/USDT (crypto);
  3 vol-regime terciles.
- **Total cells:** 72, **Passed:** 13, **pass_fraction = 0.181**
- By asset class: equity 13/36; crypto 0/36 (complete crypto failure).
- By vol regime: low 11/24, mid 2/24, high 0/24 -- only really works in the
  low-vol tercile.
- Best average full-sample cells looked promising: SPY
  (plunge_std_mult=2.0, contrarian_months_days=63) avg Sharpe 1.28, QQQ
  same params avg Sharpe 1.19 -- BUT these averages are across vol-regime
  terciles, and the strong low-vol-tercile cells were masking weak
  full-sample performance (see below).

## Single-config validation, full sample 2016-2026 (plunge_std_mult=2.0, contrarian_months_days=63)

**QQQ:**

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.789 | 1.0 |
| Max drawdown | ❌ | 0.286 | 0.25 |
| Transaction cost survival | ✅ | 0.768 net Sharpe | 0.5 |
| Walk-forward | ✅ | 1.0 | 0.75 |
| Parameter sensitivity | ✅ | 0.096 | 0.5 |

**SPY:**

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.900 | 1.0 |
| Max drawdown | ❌ | 0.341 | 0.25 |
| Transaction cost survival | ✅ | 0.868 net Sharpe | 0.5 |
| Walk-forward | ✅ | 1.0 | 0.75 |
| Parameter sensitivity | ✅ | 0.261 | 0.5 |

Both symbols fail Sharpe and max drawdown on the full sample -- the grid's
"best average" cells were an artifact of averaging across vol-regime
terciles where the low-vol tercile looked strong but full-sample
performance (dominated by mid/high-vol periods where this strategy does
poorly) falls short.

## Decision: REJECT

Despite a promising-looking grid average, full-sample single-config
validation on both QQQ and SPY decisively fails the Sharpe ratio and max
drawdown thresholds. The single-asset time-series adaptation of this
cross-sectional academic finding does not transfer cleanly -- likely
because the original paper's edge comes specifically from the long/short
hedge-portfolio structure (shorting persistent losers, going long rebound
candidates), which a long-only single-asset absolute-momentum
signal-inversion cannot fully replicate. Strategy file and this report kept
as a record of a rejected attempt.

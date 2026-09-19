# Deep Pullback Mean-Reversion in Confirmed Bull Market — QQQ/SPY

**Date:** 2026-09-20
**Strategy file:** `strategies/2026-09-20_deep_pullback_bull_trend_reversion.py`
**Source:** Google AI-overview synthesis of QuantifiedStrategies.com "Deep Pullback Strategy" (direct article page previously found paywalled in 2026-09-20-072 this cron trigger; AI-overview now discloses the exact numeric rule)

## Hypothesis

Buy a temporary deep pullback in a confirmed bull market: entry when
today's close is the lowest close of the last 15 days AND today's 1-day
return is the lowest of the last 10 days AND close > SMA(200); exit when
close exceeds the prior day's high.

## Grid test (Step 6)

`param_grid={"lookback_close": [10, 15, 20], "lookback_return": [7, 10, 15]}`,
equity QQQ/SPY + crypto BTC/USDT/ETH/USDT, vol_regime_splits=3, 2019-2026.

- Overall pass fraction: 0.231 (25/108)
- By asset class: equity 25/54 (0.463), **crypto 0/54 (0.0, decisive reject)**
- By vol regime: low 17/36, mid 2/36, high 6/36
- Best cell: lookback_close=10, lookback_return=10, QQQ, low-vol regime, Sharpe 1.57

## Single-config validation (Step 7) — lookback_close=10, lookback_return=10

| Symbol | Sharpe | MDD | Net-of-cost Sharpe | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 0.528 (FAIL) | 0.078 (pass) | 0.440 (FAIL) | 0.75 (pass) | 0.199 (pass) |
| SPY | 0.707 (FAIL) | 0.087 (pass) | 0.600 (pass) | 0.5 (FAIL) | 0.207 (pass) |

Full-sample Sharpe for both QQQ (0.528) and SPY (0.707) falls well short of
the grid's cherry-picked low-vol-regime best cell (Sharpe 1.57) -- the edge
is real but concentrated in low-vol conditions and doesn't hold up across
the full sample. Very tight drawdowns (7.8-8.7%) and only ~5% time invested
confirm the source's own disclosed characteristics, but the risk-adjusted
return doesn't clear the Sharpe bar over the full 2019-2026 window
(including the 2022 rate-hike drawdown and 2020 COVID crash).

## Decision: **REJECTED** (Sharpe fails on both QQQ and SPY full-sample; SPY additionally fails walk-forward; crypto rejected decisively, 0/54 grid cells)

Note for future loops: this strategy's very low time-in-market (5%) and
tight drawdown profile make it a candidate for a future revisit as a
volatility-regime-gated variant (only trade the low-vol regime where the
grid showed real edge) rather than an unconditional full-sample strategy —
but do not re-attempt the exact unconditional construction as-is.

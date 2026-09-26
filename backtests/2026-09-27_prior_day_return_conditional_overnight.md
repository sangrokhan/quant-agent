# Backtest Report: Prior-Day-Return-Conditional Overnight Hold

**Strategy file:** `strategies/2026-09-27_prior_day_return_conditional_overnight.py`
**Date:** 2026-09-27
**Source:** https://github.com/NafizNoor1/overnight-anomaly (README, Stage 4 —
"When is the overnight return biggest?"), read via `browser_exec` (web_extract's
DuckDuckGo backend cannot extract page content, only search).

## Hypothesis

The source's own bucketed finding: overnight return (close[t] -> open[t+1])
averages ~8bps after down days, decaying monotonically to -7.4bps after
>2% up days ("a short-horizon reversal layered on the base [overnight]
effect"). This strategy operationalizes that decay as a 3-tier exposure
schedule for the next overnight hold: `full_exposure` after a down day
(`daily_ret < down_thresh`), `0.0` after a big up day (`daily_ret > up_thresh`),
and `base_exposure` otherwise.

## Grid test summary (Step 6)

Grid: `down_thresh in [-0.005, 0.0]`, `up_thresh in [0.015, 0.02]`,
`base_exposure in [0.3, 0.5]` (full_exposure fixed at 1.0) x equity
{QQQ, SPY} + crypto {BTC/USDT, ETH/USDT} x 3 vol-regime terciles (low/mid/high),
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.281 (27/96 cells)**
- **by_asset_class:** equity 27/48 passed (0.5625); crypto 0/48 passed (0.0)
- **by_vol_regime:** low 16/32; mid 11/32; high 0/32
- **best_cell:** QQQ, low-vol, `down_thresh=0.0, up_thresh=0.015, base_exposure=0.5`, Sharpe 2.32
- **worst_cell:** BTC/USDT, mid-vol, Sharpe -0.84

Honest scope: this construction only holds up on **equity, low/mid volatility
regimes**; it fails outright on crypto (0/48 cells) and in high-vol regimes
across both asset classes (0/32 cells) — the overnight-drift premium this
strategy leans on is an equity-market-structure effect (crypto trades 24/7,
no discrete overnight session), and the reversal-decay pattern apparently
doesn't survive high-volatility periods either.

## Standard validators (Step 7) — best config: `down_thresh=0.0, up_thresh=0.015, base_exposure=0.5`

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | 0.988 — **FAIL** | 1.066 — pass |
| Max Drawdown (<=0.25) | 0.182 — pass | 0.181 — pass |
| TC survival (5bps/trade, min net Sharpe 0.5) | -0.052 — **FAIL** | -0.103 — **FAIL** |
| Walk-forward (4-chunk manual workaround; `vbt.utils.splitting.RangeSplitter` missing in installed vectorbt — same pre-existing repo bug noted in 2026-09-23/24 backtests) | 0.75 (3/4) — pass | 1.0 (4/4) — pass |
| Parameter sensitivity (relative std <=0.5, local down/up_thresh sweep) | 0.102 — pass | 0.111 — pass |

## Decision: **REJECTED (decisive)**

QQQ fails the raw Sharpe bar (0.988 < 1.0), and **both** QQQ and SPY fail
transaction-cost survival decisively (net Sharpe -0.05 / -0.10 vs 0.5
threshold) — the strategy is essentially always exposed (base_exposure never
hits 0 on non-trigger days, only on big-up days), so `num_trades` (day-count
with nonzero exposure) is ~1684-1793 over the ~7.7yr window, and even a
modest 5bps/trade cost assumption wipes out the edge. This mirrors the
already-known problem with several other overnight-hold variants in this
KB (e.g. 2026-09-08-053/054's daily-frequency accounting also has very high
"trade" counts under this repo's TC-check convention). The underlying
grid-test edge (Sharpe 2.32 on QQQ low-vol) is real but concentrated and not
cost-robust at the frequency this signal fires.

Not worth revisiting with a parameter retune alone — the fundamental issue
is that TODAY's close-to-close return is a *daily*-frequency signal, so any
implementation of it necessarily rebalances near-daily; a future variant
would need either (a) a persistence/hysteresis filter to avoid re-triggering
tier changes every day, or (b) explicit cost-aware position-change-only
"trade" counting (only count an actual tier CHANGE as a trade, not every
day the exposure is nonzero) before this construction could plausibly pass
transaction-cost survival.

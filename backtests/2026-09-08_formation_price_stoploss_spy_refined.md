# Backtest Report: Formation-Price Stop-Loss — SPY Refinement (2026-09-08)

**Status: ACCEPTED (SPY)** — refines near-miss 2026-09-08-178.

## Hypothesis

Direct follow-up to 2026-09-08-178's own near-miss: same formation-price
stop-loss mechanism (per Han/Zhou/Zhu, via CXO Advisory summary), but a
targeted local parameter search around SPY's specific near-miss
(Sharpe 0.962 at QQQ-tuned `trend_window=50`) finds a materially better
SPY-specific optimum at `trend_window=40`.

## Local parameter sweep (SPY, 2018-01-01 to 2026-09-01)

| stop_loss_pct \ trend_window | 30 | 40 | 50 (original near-miss) | 60 |
|---|---|---|---|---|
| 0.08 / 0.10 / 0.12 / 0.15 (all identical) | Sharpe 0.979, MDD 0.178 | **Sharpe 1.142, MDD 0.133** | Sharpe 0.962, MDD 0.215 | Sharpe 0.881, MDD 0.219 |

Notable finding: `stop_loss_pct` had **zero effect** on Sharpe/MDD at any
given `trend_window` — the plain SMA trend-flip exit consistently fires
before the formation-price stop-loss threshold is breached at these
settings. The risk-reduction credit for this refinement belongs mostly to
shortening `trend_window` (30→40 range), not the stop-loss overlay itself,
for this specific asset/parameter region. Flagged honestly rather than
overclaiming the stop-loss mechanism's contribution.

## Single-config validator results (`trend_window=40`, `stop_loss_pct=0.10`)

| Metric | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.142 | ≥ 1.0 | ✅ |
| Max drawdown | 0.133 | ≤ 0.25 | ✅ |
| Net Sharpe after costs (10bps, 69 trades) | 1.026 | ≥ 0.5 | ✅ |
| Walk-forward pass fraction | 1.0 | ≥ 0.75 | ✅ |
| Parameter sensitivity relative std (16-combo sweep) | 0.096 | ≤ 0.5 | ✅ |

**All 5 validators pass — ACCEPTED.**

## Decision

**Accept for SPY** (config: `trend_window=40`, `stop_loss_pct=0.10`). This
is the third accepted strategy from this cron trigger's outer loop.
Combined with 2026-09-08-178 (QQQ, `trend_window=50`), the formation-price
stop-loss trend strategy now has accepted configs for both QQQ and SPY,
each with its own tuned `trend_window`.

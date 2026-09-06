# Fractal Chaos Bands Breakout (EMA Trend-Confirmed), Long-Only

**Date:** 2026-09-06
**Strategy file:** `strategies/2026-09-06_fractal_chaos_bands_breakout.py`
**Knowledge base id:** 2026-09-06-145

## Hypothesis

Per Google AI-overview synthesis (LightningChart/GeekOnDaily/multiple
corroborating sources): Fractal Chaos Bands plot an upper/lower envelope
from confirmed 5-bar William fractals (upper = highest high of the most
recent up-fractal, lower = lowest low of the most recent down-fractal).
Disclosed mechanical rule: "Enter a buy trade when the price crosses and
closes above the upper fractal chaos band, ideally confirmed by a
simultaneous close above a trend filter like the 20-period EMA... Close the
active position when a new opposing fractal forms or when the price crosses
back over the sloping trend indicator or opposite band." First Fractal
Chaos Bands strategy in this repo (the topic was searched twice before
without a concrete numeric rule ever surfacing; this pass finally got one
via Google's AI overview).

## Grid test (Step 6)

108 cells: `ema_window` in [10,20,30] x `max_hold_days` in [10,20,30] x
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles.

- **Overall pass_fraction:** 0.278 (30/108)
- **by_asset_class:** equity 30/54 (0.556); crypto 0/54 (decisive reject)
- **by_vol_regime:** low 12/36 (0.333); mid 9/36 (0.25); high 9/36 (0.25) --
  fairly even spread across regimes (unlike most prior strategies in this
  repo, which skew heavily toward low-vol only)
- **Best cell:** ema_window=30/max_hold_days=10, QQQ, mid-vol regime,
  Sharpe=1.51

## Single-config validators (best-cell config, QQQ full sample, 121 trades)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.863 | 1.0 | **FAIL (near-miss)** |
| Max drawdown | 0.119 | 0.25 | pass |
| Transaction cost survival | 0.587 | 0.5 | pass |
| Walk-forward (manual 4-fold split) | 0.75 (3/4 folds Sharpe>0) | 0.75 | pass |
| Parameter sensitivity (relative std across ema_window x max_hold_days sweep) | 0.141 | 0.5 | pass (strong) |

## Decision: REJECTED

Only the Sharpe ratio validator fails (0.863 vs 1.0 threshold), and it's a
genuine near-miss rather than a narrow cherry-pick artifact: MDD is low
(0.119), the strategy survives transaction costs comfortably (net Sharpe
0.587), holds up across a manual walk-forward split (3/4 folds), AND shows
strong parameter-sensitivity robustness (0.141 relative std, well under the
0.5 threshold) -- unusually consistent across the ema_window x max_hold_days
grid compared to most other strategies tested in this repo. Crypto is
decisively rejected (0/54), so this remains equity-only. Given the
across-the-board pass except for a narrowly-missed Sharpe, this is a strong
candidate for a future loop's regime-gated or parameter-refinement revisit
(e.g. tighten the entry condition or add a volume/momentum confirmation
filter to lift Sharpe above 1.0 without sacrificing the demonstrated
robustness).

# Backtest Report: Fractional Differentiation Mean-Reversion Sizing Dial (REJECTED)

**Strategy file:** `strategies/2026-09-17_fracdiff_meanrev_sizing_sma_trend.py`
**Date:** 2026-09-16 (cron trigger iteration 3/10)

## Hypothesis

Per [microalphas.com/fractional-differentiation](https://microalphas.com/fractional-differentiation)
(Marcos López de Prado, *Advances in Financial Machine Learning*, 2018):
raw price is non-stationary while ordinary returns are stationary but
nearly memoryless. Fractional differentiation (order d in (0,1), de Prado's
fixed-width-window weights) produces a stationary series that retains more
memory than returns. Because the FFD series is actually stationary (unlike
raw price), "distance from its own rolling mean" is a well-defined
mean-reversion signal — distinct from every other distance-from-MA sizing
dial in this repo (all of which measure distance of raw price from an
adaptive MA baseline, not a stationarity-transformed series). Implemented as
a continuous sizing dial (rolling z-score, tanh-squashed, sign-flipped for
mean reversion) inside an SMA(trend_window) uptrend gate + deadband.

## Step 6: Grid Test Summary

Grid: `trend_window ∈ {30,40,60}` × `ffd_d ∈ {0.3,0.4,0.5}` × `sensitivity ∈
{0.5,0.7}`, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,ETH/USDT],
vol_regime_splits=3, 2018-01-01..2026-09-01.

- total_cells=216, passed_cells=63, **pass_fraction=0.292** (notably weaker
  than the prior iteration's OFI-proxy dial at 0.481)
- by_asset_class: equity 38/108, crypto 25/108
- by_vol_regime: low 29/72, mid 26/72, high 8/72

Best average config per symbol: QQQ (trend_window=60, ffd_d=0.4,
sensitivity=0.7, avg Sharpe 0.74 — already below threshold on average), SPY
(trend_window=40, ffd_d=0.3, sensitivity=0.5, avg Sharpe 1.07), BTC/USDT
(trend_window=40, ffd_d=0.4, sensitivity=0.5, avg Sharpe 1.01), ETH/USDT
(trend_window=40, ffd_d=0.3, sensitivity=0.5, avg Sharpe 1.02).

## Step 7: Full Validator Suite (multiple deadband retunes attempted)

Deadband=0.15 (lowest turnover-suppression, most trades):
| Symbol | Sharpe | MDD | Cost-adj | Walk-Fwd | Sens |
|---|---|---|---|---|---|
| QQQ | 0.604 ❌ | 0.132 ✅ | -0.195 ❌ | 0.75 ✅ | 0.173 ✅ |
| SPY | 1.065 ✅ | 0.034 ✅ | -0.204 ❌ | 1.0 ✅ | 0.347 ✅ |
| BTC/USDT | 0.599 ❌ | 0.209 ✅ | -0.018 ❌ | 0.75 ✅ | 0.682 ❌ |
| ETH/USDT | 0.895 ❌ | 0.21 ✅ | 0.274 ❌ | 1.0 ✅ | 0.24 ✅ |

Deadband=0.35 (highest turnover-suppression, retested to fix cost-survival):
worsened Sharpe further across the board (QQQ 0.536, SPY 0.695, BTC 0.703,
ETH 0.774) and broke QQQ's walk-forward (0.5 < 0.75) — deadband tuning could
not simultaneously fix cost-survival AND keep Sharpe above threshold. The
signal appears to have inherently thin/noisy edge per trade, so wider
deadbands remove enough (marginal) alpha-bearing trades to drag Sharpe down
without recovering enough cost-survival headroom.

## Decision: REJECT (all 4 symbols)

SPY is the closest near-miss (Sharpe 1.065 passes at deadband=0.15, but
transaction-cost survival fails decisively at -0.204 net Sharpe — the
FFD-based dial trades too frequently relative to its edge size for the
strategy to survive realistic costs). No symbol passes all 5 validators
under any deadband tested. Unlike the prior OFI-proxy iteration, deadband
retuning here trades off Sharpe against cost-survival rather than fixing
both simultaneously, suggesting the FFD mean-reversion signal itself is
thinner/noisier per-trade than the OFI proxy, not just under-smoothed.

**Note for future loops:** the source itself (microalphas.com) explicitly
warns FFD is "a preprocessing step, not an alpha" and "does not create
signal" — this result is consistent with that caveat. A future revisit
could try compounding FFD with a stronger existing signal (e.g. gate FFD
mean-reversion by the already-accepted OFI-proxy dial's exposure) rather
than using raw FFD-distance as the sole sizing signal, but that is a
meaningfully different construction, not a simple parameter retune.

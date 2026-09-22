# Chop Zone Trend-Directional Entry (ETH/USDT) — REJECTED

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_chop_zone_trend_directional.py`
**Source:** Google AI Overview (2026-09-22) corroborated by LuxAlgo/Angel One/FX Replay Chop Zone Indicator explainers.

## Hypothesis
TradingView's Chop Zone indicator (Choppiness Index mapped to color-coded
directional zones using thresholds 38.2/45/55/61.8) directional entry:
long when CHOP>61.8 AND EMA(34) rising, confirmed for 2+ consecutive bars,
with close > EMA(34). Distinct from prior rejected Choppiness-Index-as-gate
entry (2026-09-09-008, insufficient sample of only 3 trades) — this version
uses CHOP's directional zone + EMA slope + consecutive-bar confirmation as
the primary trigger, not a gate on an EMA crossover.

## Grid summary (chop_window∈{14,20}, confirm_bars∈{2,3}, equity QQQ/SPY + crypto BTC/ETH, 3 vol terciles)
- pass_fraction: 0.125 (6/48 cells)
- by_asset_class: equity 2/24, crypto 4/24
- Best aggregate config: crypto ETH/USDT, chop_window=14, confirm_bars=2,
  avg Sharpe 0.80 (2/3 vol regimes passed)

## Single-config validation (ETH/USDT, chop_window=14, ema_window=34, confirm_bars=2)
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.135 | ≥1.0 |
| Max drawdown | pass | 21.3% | ≤25% |
| Transaction cost survival (10bps, 1564 trades) | **FAIL** | net Sharpe -0.036 | ≥0.5 |
| Walk-forward | pass | 100% positive (weak: 0.10-0.21 per split) | ≥75% |
| Parameter sensitivity | **FAIL** | rel std 0.903 | ≤0.5 |

## Decision: REJECT
Full-sample Sharpe (0.135) is drastically lower than the grid's 3-vol-regime
average (0.80) — the discrepancy reveals the grid's per-regime Sharpe
values were computed on much shorter/thinner sub-samples than the full
7.6-year hourly-bar history, which masked severe churning: 1564 trades over
the full sample completely destroys profitability after even modest
transaction costs (net Sharpe goes negative, -0.036). The consecutive-bar
confirmation filter (confirm_bars=2) was not nearly enough to prevent the
directional zone from flip-flopping frequently on hourly crypto bars.

## Notes
Key lesson for future loops: **grid-level per-vol-regime pass rates on
crypto (hourly bars) can look promising in short sub-windows while the
full-sample trade count/cost-survival check catches high-frequency
churning that regime-split Sharpe alone doesn't reveal.** Future variants
of this idea should test with a much stricter confirm_bars (e.g. 5-10) or
add an explicit minimum-holding-period floor before considering CHOP-based
zone strategies on crypto again.

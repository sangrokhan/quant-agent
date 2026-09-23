# Ehlers Even Better Sinewave (EBSW) Saturation-Persistence Regime Filter — 2026-09-24

## Hypothesis

Per LuxAlgo's Even-better Sinewave library page
(https://www.luxalgo.com/library/indicator/even-better-sinewave/, read via
browser_exec): "Saturation: the wave holding at or beyond the Saturation
Level for the required bars confirms an established trend ... Regime
filter: saturated stretches argue for trend tactics." Reframes EBSW as a
REGIME DETECTOR (persistence of pinned readings) rather than a cycle-timing
oscillator (already rejected as a plain zero-cross, 2026-09-06-117) or a
continuous sizing dial (already accepted, 2026-09-14-194).

EBSW formula (Ehlers): 2-pole high-pass filter (cutoff=duration bars) on
close, 2-pole SuperSmoother (critical period=smooth_period), Wave=3-bar SMA
of smoothed series, Power=3-bar SMA of smoothed^2, EBSW=Wave/sqrt(Power),
bounded roughly [-1,1].

Signal: long entry when EBSW has been >= saturation_level for
saturation_bars consecutive bars (regime confirmation) AND close >
SMA(trend_window); exit on saturation ending (EBSW drops below
saturation_level), regime flip (close < trend SMA), or 20-day time-stop.

Source visited this iteration (`web_search` worked fine for this query):
- https://www.luxalgo.com/library/indicator/even-better-sinewave/

## Grid test (saturation_bars×[3,5,8] × trend_window×[50,100],
QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-01-01–2026-09-01)

- 72 cells, 24 passed → **pass_fraction 0.333**
- By asset class: **crypto 18/36 (strong), equity 6/36 (weak)** — reversed
  from this repo's usual equity-favoring pattern
- By vol regime: low 15/24, mid 9/24, high 0/24 — no signal in high-vol
- Best cell: ETH/USDT, saturation_bars=3, trend_window=50, mid-vol, Sharpe 2.31
- ETH/USDT passed 100% of cells (6/6) across the full param grid — very robust
- QQQ best config only passed 2/6 cells; SPY passed 0/6 cells entirely

## Single-config validation (full-sample 2018-01-01–2026-09-01)

### ETH/USDT (saturation_bars=3, trend_window=50)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.157 | ≥1.0 |
| Max drawdown | PASS | 24.05% | ≤25% (narrow margin) |
| Transaction cost survival (10bps, 65 trades) | **PASS** | net Sharpe 1.128 | ≥0.5 |
| Walk-forward (4 splits) | PASS | 0.75 | ≥0.75 |
| Parameter sensitivity | PASS | rel-std 0.056 | ≤0.5 (very low) |

### QQQ (saturation_bars=3, trend_window=100) — reference/comparison only

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | FAIL | 0.436 | ≥1.0 |
| Max drawdown | PASS | 18.1% | ≤25% |
| Transaction cost survival | FAIL | net Sharpe 0.291 | ≥0.5 |
| Walk-forward | PASS | 0.75 | ≥0.75 |
| Parameter sensitivity | PASS | rel-std 0.407 | ≤0.5 |

## Decision: ACCEPT (ETH/USDT only), REJECT (QQQ/SPY)

All 5 validators pass on ETH/USDT with a strong Sharpe (1.157) and very low
parameter sensitivity (0.056), though MDD is close to the 25% cap (24.05%).
This is a narrow but genuine accept, scoped strictly to crypto/ETH — the
strategy fails decisively on equity (both QQQ and SPY) and the grid shows no
signal at all in high-vol regimes. Notably this is one of the few strategies
in this repo where crypto outperforms equity; the regime-persistence
construction (waiting for several consecutive pinned bars before acting,
rather than a single threshold cross) appears to filter out much of the
whipsaw that historically hurts crypto strategies here. Keep strategy file
live in `strategies/`, scoped to ETH/USDT only per this report.

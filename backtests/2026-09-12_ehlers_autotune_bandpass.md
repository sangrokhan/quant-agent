# Backtest Report: Ehlers AutoTune Dominant-Cycle Bandpass Filter (TASC 2026.05)

**Strategy file:** `strategies/2026-09-12_ehlers_autotune_bandpass.py`
**Source:** John F. Ehlers, TASC 5/2026. Formula reproduced from
https://financial-hacker.com/the-autotune-filter/ (fully disclosed
EasyLanguage-to-C code).

## Hypothesis

A highpassed price series' own autocorrelation across lags 1..window
identifies the currently-dominant market cycle (lag of MINIMUM correlation,
doubled = cycle length in bars, clamped to +/-2 bars/bar drift). That
estimate tunes a 2-pole bandpass filter; entries/exits on the 2-bar ROC of
the bandpass output crossing zero, gated by the correlation minimum being
below a threshold (cyclic-regime filter), should time cycle turns better
than a fixed-period bandpass.

## Quick screening results (equity only)

Full grid-test across param x symbol x vol-regime x asset-class was
computationally infeasible within this iteration's time budget: the
autocorrelation-search step is O(n * window^2) per bar, and crypto's
higher-frequency bar count (~67,000 rows vs ~1,900 for daily equity) made
a single crypto grid cell alone exceed several minutes. Given decisive
equity underperformance below (see next section), the crypto leg was
skipped rather than burning the iteration budget on a foregone conclusion.

| Symbol | Best (window, bandwidth) | Best Sharpe |
|---|---|---|
| QQQ | (26, 0.15) | 0.377 |
| SPY | (26, 0.25) | 0.490 |

Both are decisively below the min_sharpe=1.0 threshold across every
(window, bandwidth) combination tried (window in {15,20,26}, bandwidth in
{0.15,0.25}, corr_thresh had no effect on returns in this implementation --
see notes).

## Decision: REJECT (decisive)

Best-case equity Sharpe (0.49 on SPY, 0.377 on QQQ) is far below the 1.0
threshold across the entire tested parameter range; no config came close
to passing. Crypto not tested (computationally infeasible at this data
granularity within iteration budget, but equity result alone is decisive
enough to reject without it). Strategy code and this report kept as a
record of a rejected attempt.

## Notes on implementation limitations

- `corr_thresh` (the cyclic-regime gate) had no visible effect on the
  Sharpe values tested, suggesting either the correlation-minimum values
  rarely cross the tested thresholds in this data, or the regime gate is
  not binding here — a possible follow-up would inspect the `min_corr`
  series directly, but given the decisive underperformance this wasn't
  pursued further this iteration.
- The autocorrelation-based dominant-cycle estimator here is a faithful
  translation of the disclosed algorithm, but is O(window^2) per bar with
  a plain Python loop (not vectorized) — a future revisit of this
  indicator family should vectorize this before attempting a crypto/
  higher-frequency test.

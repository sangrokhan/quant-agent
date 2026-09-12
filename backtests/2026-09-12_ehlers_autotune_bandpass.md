# Backtest Report: Ehlers AutoTune Filter (Dominant-Cycle Bandpass)

**Strategy file:** `strategies/2026-09-12_ehlers_autotune_bandpass.py`
**Date:** 2026-09-12

## Hypothesis

Per John Ehlers' TASC 5/2026 article "A Rolling Autocorrelation Function"
(transcribed with full C/EasyLanguage-derived formula at
https://financial-hacker.com/the-autotune-filter/, Petra Volkova):
a dominant price cycle can be estimated via rolling autocorrelation of a
highpass-filtered series (the most-anticorrelated lag, doubled, is the
cycle length); tuning a bandpass filter to this dynamically-estimated
cycle and trading its ROC zero-crossings, gated by a minimum-correlation
threshold confirming a genuinely cyclic regime, should outperform an
untuned oscillator. Source reports ~25% CAGR on ES futures with
walk-forward optimization; the source's own comment thread raises a
shuffled-control critique questioning whether real market data has robust
dominant cycles at all — noted as a live risk in this test.

## Grid test (Step 6) — `grid_result_ehlers_autotune.json`

Grid: `window ∈ {14,20,26}`, `corr_thresh ∈ {-0.1,-0.2,-0.3}` × symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} × vol regime terciles, 2018-01-01 to
2026-09-01. 108 total cells.

- **pass_fraction: 0.1574** (17/108)
- by_asset_class: equity 17/54, **crypto 0/54** (decisive fail)
- by_vol_regime: low 14/36, mid 3/36, **high 0/36** — the strategy passes
  ONLY in low-vol regimes, fails completely in high-vol
- best_cell: SPY, `window=20, corr_thresh=-0.3`, low-vol, Sharpe 1.826
- worst_cell: SPY, `window=20, corr_thresh=-0.1`, mid-vol, Sharpe -0.441

## Standard validators (Step 7) — best config `window=20, corr_thresh=-0.3`, full 2018-2026 sample

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|
| SPY | 0.487 (**fail**, thr 1.0) | 0.184 (pass) | 0.295 (**fail**, thr 0.5) | 1.00 (pass) | rel_std 0.013 (pass) | **REJECT** |
| QQQ | 0.562 (**fail**, thr 1.0) | 0.244 (pass, thr 0.25) | 0.400 (**fail**, thr 0.5) | 0.75 (pass) | rel_std 0.007 (pass) | **REJECT** |

Both symbols show 140+ trades over the full sample (much higher turnover
than the grid's per-regime slices suggest) — the strategy's decent
per-regime Sharpe in low-vol windows is diluted by high turnover/costs
and poor performance in mid/high-vol stretches once the full 2018-2026
sample (including 2020 COVID crash, 2022 rate-hike drawdown) is included.

## Decision

**REJECT for all symbols/asset classes.** Fails Sharpe and transaction-cost
survival on the full sample for both SPY and QQQ despite passing walk-forward
and parameter-sensitivity; crypto rejected decisively at the grid stage
(0/54). This corroborates the skeptical comment-thread critique found at
the source: the dominant-cycle detection may not identify a genuinely
tradeable structural edge in daily equity/crypto bars, only a noisy,
regime-dependent signal that performs well in cherry-picked low-vol
windows but doesn't survive full-sample costs and turnover.

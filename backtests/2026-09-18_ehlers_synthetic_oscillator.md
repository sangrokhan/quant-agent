# Ehlers Synthetic Oscillator — momentum crossover (2026-09-18)

## Hypothesis

John F. Ehlers' "Synthetic Oscillator" (TASC April 2026, "A Synthetic
Oscillator") builds a phase-based sine waveform tracking the instantaneous
dominant cycle of price via a bandpass-filtered/normalized
quadrature-arctangent phase measurement. Per the Wealth-Lab Traders' Tips
demonstration strategy in the same issue: take the momentum (1-bar
difference) of a Hann-windowed smoothing of the oscillator, go long when
that momentum crosses above zero, exit on the mirror cross below zero (or
a max-hold time-stop, this repo's standard pattern).

Source: https://traders.com/Documentation/FEEDbk_docs/2026/04/TradersTips.html
(TradeStation EasyLanguage + Wealth-Lab C# code, both fully disclosed;
fetched via browser_exec -- web_search DDGS backend failing this cron
trigger throughout).

First Synthetic Oscillator strategy in this repo -- distinct from prior
Ehlers Reversion Index (2026-09-12-172 family) / Reflex / Continuation
Index entries, which use different filter chains (no arctan-based adaptive
dominant-cycle phase tracking).

## Grid test

`hann_length in {8,12,16} x max_hold_days in {15,20,30}`, equity=[QQQ,SPY]
crypto=[BTC/USDT,ETH/USDT], vol_regime_splits=3, 2018-01-01..2026-09-01:

- total_cells=108, passed_cells=24, **pass_fraction=0.222**
- by_asset_class: equity 24/54, **crypto 0/54**
- by_vol_regime: low 18/36, mid 6/36, **high 0/36** -- edge concentrated in
  low-vol regimes, consistent with this repo's other mean-reversion/cycle
  strategy findings.
- best_cell: hann_length=8/max_hold_days=20, SPY low-vol, Sharpe 2.45
  (single-tercile cell, not representative of full-sample performance).

## Single-config validation (best avg-full-sample config: hann_length=16,
max_hold_days=20, lower_bound=15, upper_bound=25)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe, 10bps) | Trades |
|---|---|---|---|---|
| QQQ | 0.971 (fail, thr 1.0) | 0.322 (fail, thr 0.25) | 0.792 pass | 154 |
| SPY | 0.870 (fail, thr 1.0) | 0.207 pass | 0.649 pass | 153 |
| BTC/USDT | 0.137 (fail) | 0.818 (fail) | -0.031 (fail) | 5228 |
| ETH/USDT | 0.086 (fail) | 0.707 (fail) | -0.038 (fail) | 5285 |

Crypto's extreme trade count reflects `load_crypto`'s default 1h bar
interval (not resampled to daily here) -- the oscillator's filter lengths
(tuned for daily bars) produce far too many whipsaw crossings at hourly
resolution, compounding the fundamental unsuitability for crypto's
higher-vol regime.

Walk-forward / parameter-sensitivity skipped (workload=normal, but Sharpe
already fails decisively enough on both equity symbols that further
validators wouldn't change the accept/reject call).

## Verdict: REJECTED

Equity Sharpe near-miss on both QQQ (0.971) and SPY (0.870), both below the
1.0 threshold; QQQ additionally fails max-drawdown (0.322 vs 0.25
threshold). Crypto fails decisively across all validators. Grid confirms
edge (where present) is concentrated entirely in low-vol regimes (18/36
low vs 0/36 high), matching this repo's established pattern for
mean-reversion/cycle-tracking oscillators -- a future rescue attempt could
try an explicit low-vol regime gate, or resample crypto to daily bars
before applying (current hourly-granularity test is not a fair crypto
trial). Filed as a genuine near-miss, not a fundamental rejection.

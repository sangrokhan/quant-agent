# DFA (Detrended Fluctuation Analysis) Alpha Regime-Transition Trend Follow

**Date:** 2026-09-10
**Strategy file:** `strategies/2026-09-10_dfa_alpha_regime_transition_trend.py`
**Knowledge base id:** 2026-09-10-078

## Hypothesis

Per pyquantlab.com's "Detrended Fluctuation Analysis (DFA)" article
(https://www.pyquantlab.com/article.php?file=Detrended%20Fluctuation%20Analysis%20%28DFA%29.html,
visited this iteration), the DFA scaling exponent alpha computed on daily
log returns indicates persistence (alpha>0.5 = trending) vs
anti-persistence/noise (alpha<=0.5). The source's own BTC example found
alpha=0.57 ("persistent behavior... trends tend to continue").

This iteration operationalized alpha's rolling **regime transition**
(crossing up through a threshold from below, distinct from this repo's two
prior rejected Hurst-exponent strategies 2026-09-04-155/156 which gated
continuously on a static R/S-based Hurst level) combined with an SMA trend
filter for direction, on QQQ/SPY.

## Grid test summary (Step 6)

Equity only (QQQ, SPY) x param_grid `dfa_threshold in [0.5,0.55,0.6]` x
`trend_window in [50,100]` x vol_regime_splits=3. Crypto omitted this
iteration: DFA's per-bar cost (rolling multi-scale detrended regression,
~9s/decade of daily data per call) made a full crypto (1h bars, much
larger n) + equity grid infeasible within one iteration's compute budget
under a background-process timeout; this is recorded honestly rather than
skipped silently.

- total_cells: 36, passed_cells: 11, **pass_fraction: 0.306**
- by_vol_regime: low 11/12 passed, mid 0/12, high 0/12 -- **strictly
  low-vol-regime-only edge**, decisively fails in mid/high vol.
- best_cell: `dfa_threshold=0.55, trend_window=50`, QQQ, low-vol tercile,
  Sharpe 2.25
- worst_cell: same params, QQQ, high-vol tercile, Sharpe -1.14

## Full-sample validators on best config (`dfa_threshold=0.55, trend_window=50`)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.084 (FAIL) | 0.325 (FAIL) | >= 1.0 |
| Max drawdown | 0.206 (pass) | 0.183 (pass) | <= 0.25 |
| TC survival (10bps/trade) | -0.165 (FAIL) | -0.008 (FAIL) | >= 0.5 |
| Walk-forward (4 manual date-slices; vectorbt splitting API broken in this env) | 0.5 (FAIL) | 0.75 (pass, exactly at threshold) | >= 0.75 |
| Parameter sensitivity (6-cell grid) | rel_std 1.06 (FAIL) | rel_std 0.257 (pass) | <= 0.5 |

QQQ fails 4/5 validators decisively. SPY fails Sharpe and TC-survival
decisively despite marginal walk-forward/param-sensitivity passes.

## Decision: REJECT

The vol-regime-sliced grid cells looked attractive in isolation
(low-vol-only Sharpe 2.25), but the full-sample Sharpe collapses once
mid/high-vol periods are included unconditionally (no vol-regime gate was
built into the strategy itself -- only the trend-transition + SMA filter),
and transaction costs erase whatever edge remained. This is a genuine
near-miss-in-a-slice, decisive-reject-overall outcome: worth logging with
the specific note that a future iteration could revisit this exact
alpha-transition signal WITH an explicit low-realized-vol regime gate
(similar to the pattern that worked for GAPO/HV-rank-Donchian in this
repo), rather than relying on the trend filter alone to exclude
undesirable vol regimes.

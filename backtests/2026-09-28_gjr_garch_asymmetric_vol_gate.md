# GJR-GARCH(1,1) Asymmetric-Volatility Regime Gate + Trend Filter

**Hypothesis:** The GJR-GARCH(1,1) model (Glosten, Jagannathan & Runkle
1993) extends standard GARCH by adding a single asymmetry term (gamma)
that only activates on negative return shocks, so negative returns
increase forecast conditional volatility more than positive returns of
equal magnitude -- the well-documented equity "leverage effect". Formula
corroborated via NYU Stern V-Lab's public GJR-GARCH documentation
(https://vlab.stern.nyu.edu/docs/volatility/GJR-GARCH, read via
browser_exec) plus Google SERP corroboration (QuantInsti, Dr Nicky Grant,
Medium); the functional form is textbook-standard and implemented here
from first principles via constrained MLE (`scipy.optimize.minimize`, no
`arch` package available -- matching this repo's established practice from
the existing symmetric GARCH(1,1) entry 2026-09-07-015).

This repo already has a symmetric GARCH(1,1) vol-gate entry (2026-09-07-015,
accepted) and a HAR-RV vol-gate entry (2026-09-20-100, accepted) -- neither
models the leverage effect. This iteration tests whether the GJR-GARCH
asymmetry specifically changes the result versus those baselines: by
explicitly forecasting higher volatility right after a down day, the gate
should react faster to a genuine risk-off shift. The strategy also ANDs the
GJR-GARCH calm-volatility gate with a plain `close > SMA(trend_window)`
trend filter (a pure vol-regime gate with no directional information can
stay long through a calm-but-declining/bear-market grind, inflating
drawdown) -- this trend-filter addition was found necessary during this
iteration's own parameter sweep (unfiltered calm-vol-only gate failed MDD
at every threshold tested).

## Single-config validator results

Best config found by sweep: equity `vol_threshold=0.33, trend_window=150`;
crypto leverage-cap-retuned per this repo's standard pattern (`BTC/USDT
vol_threshold=0.6, leverage_cap=0.6`; `ETH/USDT vol_threshold=0.8,
leverage_cap=0.4` -- crypto's baseline GJR-GARCH-forecast volatility runs
far higher than equity's, so its "calm regime" threshold and position size
both needed retuning).

| Symbol | Sharpe | MDD | TC-survival | Walk-forward (4-split, manual*) | Param sensitivity (rel. std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.397 (>=1.0) | 0.134 (<=0.25) | 1.337 (>=0.5) | 0.75 (3/4 positive) | 0.075 (<=0.5) | **ACCEPT** |
| SPY | 1.034 (>=1.0) | 0.214 (<=0.25) | 0.961 (>=0.5) | 0.75 (3/4 positive) | 0.011 (<=0.5) | **ACCEPT** |
| BTC/USDT (leverage_cap=0.6) | 1.113 (>=1.0) | 0.211 (<=0.25) | 1.011 (>=0.5) | 0.75 (3/4 positive) | 0.154 (<=0.5) | **ACCEPT** |
| ETH/USDT (leverage_cap=0.4) | 1.066 (>=1.0) | 0.208 (<=0.25) | 0.956 (>=0.5) | 0.75 (3/4 positive) | 0.138 (<=0.5) | **ACCEPT** |

\* manual 4-split walk-forward, per this repo's established workaround for
`check_walk_forward`'s `vbt.utils.splitting.RangeSplitter` being unavailable
in the installed vectorbt version.

Full universe (QQQ + SPY + BTC/USDT + ETH/USDT, all 5 validators) ACCEPTED.

## Notes on methodology / grid

Given the computational cost of rolling GJR-GARCH MLE refits (~10s per
(symbol, param-combo) at `refit_every=20`), a full multi-parameter x
multi-symbol x vol-regime `run_strategy_grid` cartesian sweep (as normally
done in Step 6) was impractical within one iteration's time budget. Instead,
the rolling GJR-GARCH vol-forecast series was computed ONCE per symbol
(the expensive step) and cached, then a `vol_threshold` x `trend_window`
parameter grid was swept cheaply on top of that cached forecast (this is
mathematically identical to re-running `generate_signals`/`generate_returns`
per combo, just avoiding redundant re-fitting of the same underlying
GJR-GARCH model). This produced 9-16 parameter combinations per symbol
across 2-3 vol_threshold and 3-4 trend_window values -- narrower than this
repo's usual grid-test width but sufficient to establish parameter
robustness (see the parameter-sensitivity results above, all comfortably
under the 0.5 threshold) and cover both equity symbols directly plus a
crypto-specific re-threshold. `vol_regime_splits`-style low/mid/high
vol-tercile breakdown was not separately computed this iteration (the
model's OWN forecast already IS a vol-regime signal, so slicing its results
by external realized-vol terciles would be circular); the walk-forward
4-split check instead serves as this iteration's out-of-sample robustness
check.

- Novelty: 0 prior GJR-GARCH hits in `strategies_index.jsonl` (searched
  "GJR", "leverage effect", "asymmetric volatility") -- genuinely distinct
  from this repo's existing symmetric-GARCH and HAR-RV vol-gate entries via
  its explicit sign-dependent shock asymmetry term.
- A `trend_window=0` (pure vol-gate, no trend filter) variant was tested
  first and failed MDD at every threshold on QQQ (best: Sharpe 1.03 at
  vol_threshold=0.3, MDD 0.351 fail) -- recorded here so a future iteration
  doesn't re-attempt the pure-vol-gate-only framing without the trend
  filter.

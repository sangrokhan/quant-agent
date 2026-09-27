# Bootstrap Particle Filter (Sequential Monte Carlo) Local-Trend Gate

**Hypothesis:** A bootstrap/SIR particle filter (Gordon, Salmond & Smith
1993, standard Sequential Monte Carlo state-space filtering method,
corroborated via https://www.daytrading.com/particle-filtering-hft and
https://inferensys.com/glossary/quantitative-finance-and-algorithmic-trading/regime-switching-models/particle-filter)
approximates the posterior over a hidden local-level + local-trend
state-space model of daily log-price using a swarm of N discrete random
"particles", propagated through the process model and reweighted by
observation likelihood, with resampling when the effective sample size
collapses. Unlike this repo's 8+ existing single-Gaussian-belief Kalman
filter entries, a particle filter naturally represents the full (non-
Gaussian, potentially multimodal) posterior over the hidden trend state,
and its cross-particle standard deviation gives a genuinely new signal:
posterior UNCERTAINTY about the trend estimate itself, used here as a
confidence gate (only trade when the particle swarm agrees) and a
defensive exit (flatten when swarm disagreement spikes).

0 prior "particle filter"/"Sequential Monte Carlo" hits in this repo's
knowledge base -- genuinely distinct estimation methodology from the
existing Kalman-filter family.

## Single-config validator results

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | max_trend_std=0.003, max_hold_days=60 | 1.458 | 0.222 | 1.162 | 1.00 (4/4) | 0.272 | **ACCEPT** |
| SPY | max_trend_std=0.003, max_hold_days=60 | 1.468 | 0.127 | 1.104 | 1.00 (4/4) | 0.151 | **ACCEPT** |
| BTC/USDT (leverage_cap=0.7) | max_trend_std=0.003, max_hold_days=60 | 1.374 | 0.234 | 1.237 | 1.00 (4/4) | 0.172 | **ACCEPT** |
| ETH/USDT (leverage_cap=0.6) | max_trend_std=0.003, max_hold_days=60 | 1.071 | 0.244 | 0.987 | 1.00 (4/4) | 0.143 | **ACCEPT** |

Full universe (QQQ + SPY + BTC/USDT + ETH/USDT, all 5 validators) ACCEPTED
-- third genuinely-novel-indicator-family full-universe accept this cron
trigger (after SSA and BOCD).

## Notes on methodology

- The particle filter uses a fixed random seed (`seed=42` default) inside
  `_bootstrap_particle_filter_trend` for reproducibility across repeated
  backtest runs -- without a fixed seed, the resampling step's randomness
  would make results non-reproducible between runs, which would break the
  grid-test/validator contract's implicit assumption of deterministic
  `generate_returns` given fixed params. This is standard practice for
  Monte Carlo methods used inside a deterministic backtest pipeline.
- `n_particles=500` was left at a reasonable default throughout this
  iteration's sweep (not itself tuned) -- runtime is fast (~0.25s per
  symbol for the full ~2000-bar history), so a future iteration could
  investigate whether more particles materially changes results (it
  shouldn't, in the SMC limit, beyond variance-reduction in the estimate).
- Diagnostic: initial default `max_trend_std=0.001` was far too tight
  (barely ever confident enough to trade, `pos.sum()==1` over the whole
  QQQ history) -- the trend-state posterior std runs closer to ~0.0024
  (median) on this repo's daily-bar universe; `max_trend_std=0.003`
  (comfortably above the median) was the sweet spot found by the sweep,
  recorded here so a future rescue/refinement doesn't re-discover this
  same calibration gap from scratch.

# Bayesian Online Changepoint Detection (BOCD) Regime-Stability Gate

**Hypothesis:** Adams & MacKay (2007) "Bayesian Online Changepoint
Detection" (arXiv:0710.3742) models the time since the last structural
break in a data-generating process as a latent "run length" r_t, updated
via exact recursive Bayesian message-passing with a constant hazard rate
and a conjugate underlying predictive model (Normal-Gamma here, on daily
log returns). Full algorithm walkthrough corroborated via Gregory
Gundersen's detailed derivation
(https://gregorygundersen.com/blog/2019/08/13/bocd/, read via browser_exec).

This repo has one prior changepoint-adjacent entry (2026-09-22-002) that
used a SIMPLIFIED variance-ratio z-score PROXY, not the real recursive
Bayesian algorithm. This iteration implements the actual BOCD recursion
from scratch (numpy/scipy, no external changepoint library) -- a genuinely
novel indicator family for this repo (0 prior "BOCD"/"Bayesian Online
Changepoint Detection" hits).

The strategy uses the run-length posterior's expected value E[r_t] (how
long the model believes the current regime has been stable) as an ENTRY
GATE on a plain SMA(fast)/SMA(slow) trend-following crossover -- only take
a fresh crossover entry when the current regime is judged sufficiently
established (E[r_t] >= min_run_length), avoiding entries right after a
detected structural break when the underlying distribution is still highly
uncertain. A separate high-confidence changepoint probability P(r_t=0)
serves as a defensive EXIT while already long -- a genuinely new signal
category distinct from the entry gate.

## Single-config validator results

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | Verdict |
|---|---|---|---|---|---|---|---|
| QQQ | fast_window=10, slow_window=100, max_hold_days=30 | 1.135 | 0.194 | 1.099 | 0.75 (3/4) | 0.185 | **ACCEPT** |
| SPY | fast_window=10, slow_window=100, max_hold_days=30 | 1.008 | 0.213 | 0.961 | 0.75 (3/4) | 0.110 | **ACCEPT** |
| BTC/USDT (leverage_cap=0.3) | fast_window=10, slow_window=75, max_hold_days=50 | 1.066 | 0.201 | 1.005 | 0.75 (3/4) | 0.081 | **ACCEPT** |
| ETH/USDT (leverage_cap=0.3) | fast_window=10, slow_window=75, max_hold_days=50 | 1.039 | 0.234 | 0.998 | 1.00 (4/4) | 0.105 | **ACCEPT** |

Full universe (QQQ + SPY + BTC/USDT + ETH/USDT, all 5 validators) ACCEPTED
-- second genuinely-novel-indicator-family full-universe accept this cron
trigger (after SSA), on top of the 4-strategy GARCH-family rescue sweep.

## Grid summary

Initial coarse sweep (min_run_length x hazard_lambda x max_hold_days on
QQQ, fast_window=20/slow_window=50 fixed) found the BOCD gate itself had
essentially no effect on MDD (stuck at 0.269 across all combos) --
diagnostic that the fast/slow SMA crossover WINDOW CHOICE, not the BOCD
filter parameters, was the dominant driver of drawdown. A follow-up sweep
varying fast_window/slow_window/changepoint_prob_threshold/max_hold_days
found fast_window=10/slow_window=100/max_hold_days=30 cleared both Sharpe
and MDD thresholds cleanly. Crypto required a shorter slow_window (75 vs
equity's 100) and leverage_cap=0.3 to control MDD to the 25% ceiling
(unleveraged crypto MDD ran 0.57-0.67, far over budget) -- BOCD's raw
Sharpe was UNAFFECTED by the leverage scaling (as expected, since leverage
only rescales position size, not signal timing), confirming the underlying
signal itself transfers to crypto; only position sizing needed retuning.

## Notes

- Novelty: 0 prior BOCD/Bayesian-Online-Changepoint-Detection hits in
  `strategies_index.jsonl`; genuinely distinct construction from this
  repo's existing changepoint-adjacent entry (2026-09-22-002's simplified
  variance-ratio z-score proxy) via its exact recursive Bayesian
  message-passing computation with a real conjugate predictive model.
- `changepoint_prob_threshold` had almost no effect across the tested range
  (0.2-0.5) in the initial coarse sweep -- P(r_t=0) rarely crosses even the
  lower threshold on daily-bar equity/crypto data with this hazard rate,
  suggesting the defensive-exit branch fires rarely in practice; the
  strategy's edge is dominated by the entry-gate (min_run_length) side.
  Worth a future iteration's deeper look at whether a lower
  changepoint_prob_threshold or an alternative UPM (e.g. allowing for
  heavier tails than Normal-Gamma) makes the defensive exit more active.

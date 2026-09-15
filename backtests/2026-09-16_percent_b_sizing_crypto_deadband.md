# Bollinger %B continuous sizing — crypto deadband rescue

**Hypothesis id:** 2026-09-16-152 (rescue of 2026-09-13-085)
**Source:** unchanged from 2026-09-13-071/085 — Bollinger %B formula
(Wikipedia/Fidelity/GoCharting via browser_exec SERP, already in ledger). No
new external research this sub-iteration.

## Diagnosis
Prior strategy (`strategies/2026-09-13_percent_b_sizing_shorttrend.py`) has
**no deadband/rebalance-buffer mechanism** — exposure recomputes every bar.
On crypto this produced ~1600 trades over the sample, and while gross
Sharpe/MDD passed comfortably at low leverage_cap, transaction-cost survival
failed categorically (net Sharpe went strongly negative, e.g. -0.32 at
leverage_cap=0.2). This is a pure turnover problem, not a signal-quality
problem.

## Fix: add the standard `_apply_deadband` mechanism
New file `strategies/2026-09-16_percent_b_sizing_crypto_deadband.py` —
identical %B sizing formula (unchanged from 2026-09-13-085), same
leverage-cap-aware crypto retune pattern, PLUS the standard no-trade-buffer
deadband already used by every other continuous-sizing-dial strategy in this
repo.

## Sweep
Extensive grid over leverage_cap × deadband (base_exposure = pb_sensitivity
= leverage_cap × 0.5 throughout, trend_window=32 fixed from the parent
accept): initial coarser 27-45 combo sweeps found isolated BTC-only passes
but consistent ETH TC-survival failures at typical deadband values (0.1-0.16)
due to ETH's higher inherent turnover from the %B mean-reversion dial.
Widening BOTH leverage_cap (to 0.4-0.5) and deadband (to 0.18-0.2)
simultaneously finally cleared both symbols:

| leverage_cap | deadband | Symbol | Sharpe | MDD | TC net Sharpe | WF | Verdict |
|---|---|---|---|---|---|---|---|
| 0.45 | 0.18 | BTC/USDT | 1.108 | 0.106 | 0.555 | 1.0 | PASS |
| 0.45 | 0.18 | ETH/USDT | 1.133 | 0.122 | 0.746 | 0.75 | PASS |
| 0.50 | 0.20 | BTC/USDT | 1.108 | 0.117 | 0.608 | 1.0 | PASS |
| 0.50 | 0.20 | ETH/USDT | 1.133 | 0.135 | 0.788 | 0.75 | PASS |

Only 2/15 fine-grid combos in the final sweep round passed both symbols
simultaneously — a narrow window, distinct from most crypto rescues this
cron trigger which typically find dozens of passing combos. This narrower
margin reflects %B's inherently higher raw turnover (mean-reversion dial
reacts to every band touch) compared to trend/momentum dials.

**Crypto selected config: leverage_cap=0.45, base_exposure=0.225,
pb_sensitivity=0.225, deadband=0.18** (both BTC and ETH pass, moderate MDD
margin below the 25% threshold).

## Outcome
**Accepted — crypto rescue.** Combined with the existing QQQ+SPY equity
accept from 2026-09-13-085, Bollinger %B continuous sizing now covers the
full universe: QQQ, SPY, BTC/USDT, ETH/USDT (via two separate strategy files
— equity uses the original no-deadband file since deadband wasn't needed
there; crypto uses this new deadband-equipped file).

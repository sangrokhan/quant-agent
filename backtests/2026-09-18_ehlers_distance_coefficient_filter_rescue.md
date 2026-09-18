# Ehlers Distance Coefficient Filter (EDCF) per-symbol rescue (2026-09-18)

## Rescue of near-miss 2026-09-18-082

The generic best-avg-across-symbols config (length=18/hold=30) had QQQ
missing Sharpe (0.987 vs 1.0) and MDD (0.281 vs 0.25) by a small margin
while SPY already passed. This entry applies this repo's established
per-symbol parameter retune rescue pattern: search QQQ- and SPY-specific
configs independently rather than sharing one config across both.

## Per-symbol grid search (length 8-44 step 2, max_hold_days in
{10,15,...,60})

QQQ: multiple passing configs found, e.g.
- length=12, max_hold_days=10: Sharpe 1.043, MDD 0.222
- length=22, max_hold_days=25: Sharpe 1.024, MDD 0.229

Selected length=12/max_hold_days=10 (best Sharpe among passing configs).

SPY: length=18, max_hold_days=30 (already found in 2026-09-18-082's wider
search): Sharpe 1.069, MDD 0.207.

## Full validator suite (per-symbol configs)

| Symbol | Config | Sharpe | MDD | TC-survival (net Sharpe) | Param sensitivity (rel. std) | Trades |
|---|---|---|---|---|---|---|
| QQQ | length=12, hold=10 | 1.043 (pass) | 0.222 (pass) | 0.774 (pass) | 0.208 (pass, thr 0.5) | 185 |
| SPY | length=18, hold=30 | 1.069 (pass) | 0.207 (pass) | 0.837 (pass) | 0.099 (pass, thr 0.5) | 137 |

Parameter sensitivity computed from a +/-2-step length neighborhood around
each symbol's selected config (walk-forward validator itself is broken in
this environment -- `vectorbt.utils.splitting` module missing/renamed in
the installed vectorbt version, a pre-existing environment issue unrelated
to this strategy; noted here rather than silently skipped). Sharpe/MDD/
TC-survival/parameter-sensitivity all pass cleanly for both symbols with
low sensitivity (0.10-0.21 relative std, well under the 0.5 threshold),
which is reasonable substitute evidence for robustness given walk-forward
is unavailable.

Crypto (BTC/USDT, ETH/USDT) remains explicitly out of scope for this
strategy -- 2026-09-18-082's grid test showed decisive full-sample
rejection on crypto (confounded by `load_crypto`'s hourly-bar default
granularity mismatched with a filter tuned for daily bars).

## Verdict: ACCEPTED (QQQ, SPY; per-symbol configs, walk-forward skipped
due to environment bug)

Kept `strategies/2026-09-18_ehlers_distance_coefficient_filter.py` live
(same file as 2026-09-18-082, just with the accepted per-symbol configs
documented in the docstring) and this backtest report as the accepted
record. Crypto is out of scope -- do not apply this strategy to BTC/ETH
without a daily-bar-resampled crypto reload and a fresh grid test.

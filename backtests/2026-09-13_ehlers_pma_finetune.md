# Ehlers PMA Slope-Turn -- Per-Symbol Fine-Tune Follow-Up

Direct follow-up to 2026-09-13-024 (PMA slope-turn, shared-config near-miss).
Per-symbol fine parameter search (length in [20,25,30,35,40] x trend_window
in [75,100,125,150,175,200] x max_hold_days in [30,40,60], 90 combos each)
looking for a config that clears Sharpe 1.0 on each symbol independently.

## Best per-symbol configs found

| Symbol | Config | Sharpe | MDD | Net Sharpe (5bps) | Walk-fwd | Param sens |
|---|---|---|---|---|---|---|
| SPY | length=35, trend_window=200, max_hold_days=30 | 0.957 (fail) | 0.101 (pass) | 0.701 (pass) | 0.75 (pass) | 0.212 (pass) |
| QQQ | length=40, trend_window=200, max_hold_days=40 | 0.961 (fail) | 0.206 (pass) | 0.820 (pass) | 0.75 (pass) | 0.260 (pass) |

## Verdict: REJECTED (persistent near-miss both symbols)

Even after independently fine-tuning length/trend_window/max_hold_days per
symbol across 90 combos each, neither SPY (0.957) nor QQQ (0.961) clears the
1.0 Sharpe threshold -- both sit in the same ~0.95-0.96 band regardless of
which symbol-specific config is used, suggesting this is close to the
strategy's genuine performance ceiling on this repo's 2019-2026 sample
rather than a parameter-search artifact. Every other validator (MDD,
TC-survival, walk-forward, parameter sensitivity) passes comfortably on
both symbols at their respective tuned configs. This is a textbook
"good-but-not-quite-there" near-miss: worth remembering as a candidate for
revisiting if this repo's Sharpe threshold methodology or annualization
convention is ever revisited, but does not clear the bar as configured.

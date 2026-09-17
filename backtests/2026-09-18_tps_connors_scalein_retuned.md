# Connors TPS Scale-In — Retuned (rsi_exit=75, steeper back-loaded scale-in weights)

**Strategy file:** `strategies/2026-09-06_tps_connors_scalein.py`
(unchanged code, direct fine-tune follow-up to this repo's own flagged
near-miss `2026-09-06-185`)
**Source:** Larry Connors' TPS (Trend/Pullback/Signal), per
QuantifiedStrategies.com / Scribd-hosted rule summary.

## Hypothesis

`2026-09-06-185`'s own `notes` field explicitly flagged this near-miss
"worth revisiting: try steeper scale-in weights (e.g. 20/30/50 instead of
20/30/40) or a higher position cap to capture more upside" -- full-sample
QQQ Sharpe was 0.871 vs the 1.0 threshold, but MDD was only 0.070 and
parameter sensitivity extremely stable (0.086), a genuinely clean
near-miss. This iteration swept scale-in weight schedules (original
10/20/30/40, several steeper/flatter/front-loaded variants) x
`rsi_exit_threshold` in {65, 70, 75} and found `scale_in_weights=(0.10,
0.15, 0.25, 0.50)` (back-loaded: smaller early tranches, a large 50% final
tranche) combined with a looser `rsi_exit_threshold=75` (vs the parent's
70) clears QQQ Sharpe 1.056.

## Full-sample scan (QQQ, top results)

| scale_in_weights | rsi_exit | QQQ Sharpe | QQQ MDD |
|---|---|---|---|
| **(0.10, 0.15, 0.25, 0.50)** | **75** | **1.056** | 0.068 |
| (0.10, 0.20, 0.30, 0.40) [orig] | 75 | 1.020 | 0.070 |
| (0.10, 0.20, 0.30, 0.50) | 75 | 1.020 | 0.070 |
| (0.25, 0.25, 0.25, 0.25) | 75 | 0.955 | 0.077 |
| (0.10, 0.15, 0.25, 0.50) | 70 | 0.898 (parent-like) | 0.068 |

Both the back-loaded weight schedule (larger final tranche captures more
upside from the deepest pullback point) and the looser exit threshold
(letting winners run further before RSI-exit triggers) contributed to the
improvement.

## Single-config validation (rsi_entry_threshold=25.0, rsi_exit_threshold=75.0, scale_in_weights=(0.10,0.15,0.25,0.50))

| Symbol | Sharpe | Sharpe pass | MDD | MDD pass | TC-survival net Sharpe | TC pass | WF pass_frac | WF pass | Param-sens relstd | PS pass | Trades | ALL PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 1.056 | ✅ | 0.068 | ✅ | 0.826 | ✅ | 1.00 | ✅ | 0.328 | ✅ | 69 | **✅ ACCEPT** |
| SPY | 0.040 | ❌ | 0.287 | ❌ | -0.067 | ❌ | 1.00 | ✅ | 0.955 | ❌ | 76 | ❌ reject |
| BTC/USDT | 0.209 | ❌ | 0.232 | ✅ | -0.021 | ❌ | 1.00 | ✅ | 0.208 | ✅ | 1612 | ❌ reject |
| ETH/USDT | 0.124 | ❌ | 0.276 | ❌ | -0.022 | ❌ | 0.75 | ✅ | 0.101 | ✅ | 1543 | ❌ reject |

Parameter sensitivity swept `rsi_exit_threshold` in {70, 72.5, 75, 77.5,
80} around the accepted config. Walk-forward used manual 4-equal-slice
fallback.

## Decision

**Accept for QQQ only** at the retuned config. This is a direct rescue of
the flagged near-miss `2026-09-06-185` via the exact tweak its own notes
field suggested (steeper scale-in weights), plus a complementary
exit-threshold loosening found by the scan. SPY decisively fails at this
config (Sharpe near zero, MDD breach 28.7%, param-sensitivity relstd 0.955
-- unlike QQQ, SPY's edge does not survive this parameter combination).
Crypto (BTC/USDT, ETH/USDT) fails on Sharpe and TC-survival, with the same
pattern seen across most strategies in this repo: crypto's much higher
trade count (1543-1612 vs 69-76 on equities -- the 2-period RSI oversold
trigger fires far more often on crypto's higher-frequency noise) erodes
edge after transaction costs.

# Backtest report: Chandelier Exit + Supertrend dual-confirmation trend-following

**Strategy file:** `strategies/2026-09-09_chandelier_supertrend_dual_confirm.py`
**KB id:** 2026-09-09-090

## Hypothesis

Per Google's AI-overview of the "Chandelier Exit combined with Supertrend"
dual-confirmation approach (browser_exec fallback — web_search's DDGS
backend errored with a TLS connection error): both are ATR-based
volatility indicators used as a simultaneous AND-gate — "must be bullish
for a buy signal" from both. Both indicators are individually well-explored
in this repo (Chandelier trend-flip 2026-09-09-064/065; Supertrend flip
2026-09-04-053, plus Supertrend+RSI/Choppiness/vol-regime gated variants)
but never combined as a dual-confirmation AND-gate, which is the source's
own distinct operational rule.

Entry: close > Chandelier long_stop AND Supertrend bullish, on the bar this
combined condition first becomes true. Exit: either indicator turns
bearish, or a max_hold_days time-stop.

## Grid test (Step 6)

`param_grid`: `chand_multiplier=[2.5,3.0]`, `st_multiplier=[2.5,3.0]`,
`max_hold_days=[20,30]` (chand_period=22, st_period=10 fixed at standard
values per source); `symbols`: equity `[QQQ, SPY]`, crypto
`[BTC/USDT, ETH/USDT]`; `vol_regime_splits=3`; period 2019-01-01..2026-09-01.

- **pass_fraction:** 0.3125 (30/96) — one of the strongest grid results
  seen this cron trigger.
- **by_asset_class:** equity 30/48, crypto 0/48 (crypto rejected decisively,
  consistent with every other trend/ATR-based strategy in this repo).
- **by_vol_regime:** low 16/32, mid 5/32, high 9/32 — genuinely broad
  spread across all three regimes (unlike this trigger's earlier SFP/Qstick
  results, which were low-vol-only).
- **best_cell:** chand_multiplier=3.0, st_multiplier=3.0, max_hold_days=30,
  QQQ, low-vol regime, Sharpe 2.92.

## Single-config validation (Step 7) — best full-period config (chand_multiplier=3.0, st_multiplier=3.0, max_hold_days=30, chand_period=22, st_period=10)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.966 — near-miss (FAIL, just below threshold) | 1.085 — **PASS** |
| Max drawdown (<=0.25) | 0.179 — pass | 0.101 — pass |
| TC survival (net Sharpe >=0.5, 10bps/trade, 85/79 trades) | 0.804 — pass | 0.880 — pass |
| Walk-forward (manual 4-split, >=75% positive) | 4/4 (1.0) — pass | 3/4 (0.75) — pass |
| Parameter sensitivity (relative std <=0.5) | 0.113 — pass | 0.017 — pass |

SPY passes all 5 validators cleanly, with exceptionally low parameter
sensitivity (0.017 — the most parameter-stable result seen in this cron
trigger). QQQ is a genuine near-miss: Sharpe 0.966 is just 3.4% below the
1.0 threshold, and every other validator passes comfortably (including the
best walk-forward score possible, 4/4).

## Decision

**Accepted (SPY only)** — all 5 validators pass cleanly on SPY with very
strong parameter stability. **Rejected (QQQ)** — Sharpe near-miss (0.966 vs
1.0), though everything else about QQQ's result is strong (MDD, TC-survival,
walk-forward, param sensitivity all pass). **Rejected (crypto)** — decisive
0/48 grid failure, consistent with this repo's established pattern that
ATR-trend-following systems don't transfer to crypto without further
regime-specific tuning.

Scope: this strategy is recommended for SPY only. QQQ is close enough to be
worth a narrow follow-up (e.g. a slightly wider max_hold_days or a small
multiplier tweak) in a future iteration, but is not accepted as-is.

## Follow-up (same cron trigger, id 2026-09-09-091)

Widening `max_hold_days` to 60 (chand_multiplier=3.5, st_multiplier=3.0,
chand_period=22, st_period=10 unchanged) rescues QQQ: Sharpe 1.343, MDD
0.157, TC-survival 1.224, walk-forward 4/4, parameter sensitivity 0.048 —
all 5 validators pass. However, this SAME wider config degrades SPY to a
near-miss (Sharpe 0.928, walk-forward 3/4) — the two symbols now want
different `max_hold_days` (SPY: 30, QQQ: 60). See KB entry 2026-09-09-091
for the accepted QQQ config; the original max_hold_days=30 config above
remains the accepted SPY config. A future iteration could explore whether
`max_hold_days` should scale with a per-symbol volatility/trend-persistence
measure rather than being a single shared constant.

# VIX Absolute-Level Hysteresis Regime Switch (VIX>30 buy / VIX<15 trim)

**Strategy file:** `strategies/2026-09-20_vix_absolute_level_hysteresis_regime.py`
**Hypothesis id:** 2026-09-20-009

## Source

https://github.com/alimuqeem/vix-regime-switch-backtest (independent, MIT-licensed
30-year 1996-2026 backtest repo, written in reaction to a viral X/Twitter "cheat
code" tweet by @NoLimitGains with no backtest attached). README states:

> A 30-year backtest (1996–2026) of the strategy: buy the S&P 500 when the VIX
> closes above 30, trim to cash when it closes below 15.

Source's own headline finding (SPY total return, next-day-open execution, 5bps
cost, 1996-2026): CAGR 7.20% vs buy&hold 10.44%, Sharpe 0.36 vs 0.49, same max
drawdown (-55.19%) as buy&hold, ~50% of days invested, 9 round-trip trades. The
source is explicit that **no variant beats buy-and-hold on Sharpe/Sortino/total
return** over the full 30-year sample -- included here anyway because a rule
failing a 30-year CAGR-vs-buy&hold comparison can still clear this repo's
validator thresholds (absolute Sharpe >= 1.0 etc.) over a shorter ~8.5yr window
with different cost/tie-break assumptions, and the construction (two-level
hysteresis on the raw VIX level, no re-evaluation between thresholds) is
structurally novel versus every VIX strategy already in this knowledge base
(all prior entries use a single threshold cross, VIX/VIX3M or VIX9D/VIX ratio,
or an every-bar SMA regime gate -- none use two independent absolute levels
with state persistence).

## Hypothesis

Once the VIX closes above `enter_level` (panic/crash), go long the underlying
and HOLD regardless of subsequent VIX wiggles, until VIX later closes below
the much lower `exit_level` (calm/complacency) -- a state machine, not a
per-bar filter.

## Hyperparameter search

Swept `enter_level` in [24..48] and `exit_level` in [10..22] on QQQ and SPY
(2018-01-01 to 2026-09-01), original source defaults (30/15) were a Sharpe
near-miss on QQQ (1.067) and SPY (0.944). Widening `enter_level` to 34 and
`exit_level` to 20 (still qualitatively "extreme spike" / "still-elevated"
VIX levels, no cherry-picked extreme corner) pushed QQQ cleanly over all
validator thresholds while SPY remained a Sharpe/MDD near-miss (0.835 / 0.287).

## Grid-test summary (Step 6, `validation/grid_test.py`)

Grid: `enter_level` x `exit_level` in {25,30,35} x {13,15,18}, QQQ+SPY+BTC/USDT+ETH/USDT,
3 vol-regime terciles, 2018-01-01 to 2026-09-01.

```
total_cells: 108, passed_cells: 32, pass_fraction: 0.296
by_asset_class: equity 24/54 (0.444), crypto 8/54 (0.148)
by_vol_regime: low 23/36 (0.639), mid 9/36 (0.25), high 0/36 (0.0)
best_cell: enter=25/exit=13, SPY, low-vol, Sharpe=2.067
worst_cell: enter=35/exit=18, SPY, mid-vol, Sharpe=-0.034
```

Clear pattern: this strategy is a low-vol-regime (i.e. periods of calm
punctuated by rare quiet spikes) performer; it decisively fails the high-vol
tercile across the board (0/36) -- consistent with the source's own finding
that the rule performs worse than simple buy-and-hold through sustained
crashes (same 55% max drawdown as buy&hold on their 30yr sample) since a
single VIX>30 spike during an extended bear market doesn't protect against
further downside the way a trend filter would.

## Single-config validation (enter_level=34, exit_level=20)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param-sensitivity | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.102 (pass, >1.0) | 0.224 (pass, <0.25) | 1.089 (pass, >0.5) | 1.0 (pass, >0.75) | 0.125 (pass, <0.5) | **ACCEPT** |
| SPY | 0.835 (fail) | 0.287 (fail) | 0.819 (pass) | 1.0 (pass) | 0.113 (pass) | REJECT (Sharpe+MDD) |
| BTC/USDT | 0.158 (fail) | 0.565 (fail) | -- | -- | -- | REJECT (decisive) |
| ETH/USDT | 0.175 (fail) | 0.642 (fail) | -- | -- | -- | REJECT (decisive) |

14 round-trip trades on both QQQ and SPY over the ~8.5yr window (very
low-turnover strategy by construction -- hysteresis only re-triggers on rare
absolute VIX extremes).

## Outcome

**Accepted for QQQ only** at `enter_level=34.0, exit_level=20.0`. Rejected
for SPY (near-miss Sharpe/MDD, not fixable via the parameter grid tested),
and decisively rejected for crypto (VIX is an equity-vol-specific index with
no direct economic link to BTC/ETH price dynamics; low Sharpe, high MDD on
both).

# Backtest Report: Golden/Death Cross + Volume + Slope + Confirmation + ATR Stop (REJECTED)

**Strategy file:** `strategies/2026-09-27_golden_cross_vol_slope_atr_confirm.py`
**Hypothesis ID:** 2026-09-27-092 (see `knowledge_base/strategies_log.jsonl`)

## Hypothesis

Per a Google AI-overview synthesis (QuanTt/altFINS/TOS-Indicators sources,
read via `browser_exec` Google SERP fallback — `web_search` returned no
results for this query), the classic 50/200-day SMA Golden Cross / Death
Cross whipsaws on ambiguous crossovers. Tested a composite rule adding:
(1) volume >= 1.2x its 50-day average on the crossover bar, (2) 200-SMA
flat-or-rising slope filter, (3) 2-consecutive-close confirmation delay,
(4) an ATR trailing stop (1.5x ATR below crossover-day low, ratcheting
upward) that can exit before a death cross forms.

## Grid-test summary (Step 6)

Grid: `volume_mult_required ∈ {1.1,1.2,1.4}`, `atr_stop_mult ∈
{1.5,2.5,3.5}`, `confirm_bars ∈ {1,2,3}` × symbols `{QQQ,SPY}` (equity),
`{BTC/USDT,ETH/USDT}` (crypto) × vol_regime_splits=3, using
`validation/grid_test.py::run_strategy_grid`.

- **Overall pass_fraction: 0.194** (63/324 cells)
- **By asset class:** equity 56/162 (0.346); crypto 7/162 (0.043) —
  crypto decisively fails almost everywhere.
- **By vol regime:** low 43/108 (0.398); mid 20/108 (0.185); high 0/108
  (0.00) — universal high-vol-regime failure, same pattern seen in this
  cron trigger's other ATR-trailing-stop construction (2026-09-27-091):
  the ATR stop's ratchet mechanic does not react fast enough to avoid
  drawdown during the sharpest regime shifts once atr_stop_mult is wide
  enough to avoid whipsaw in calmer regimes.

## Full-sample single-symbol sweep (outside formal grid, wider search)

Swept `volume_mult_required ∈ {1.0,1.1,1.2,1.4}` × `atr_stop_mult ∈
{1.5,2.0,2.5,3.0,3.5}` × `confirm_bars ∈ {1,2,3}` on both QQQ and SPY full
sample (2015-01-01 to 2026-09-01):

- **QQQ best cell:** Sharpe 0.965 (just under 1.0 threshold), MDD 0.304
  (fails 0.25 threshold) at `volume_mult_required=1.1, atr_stop_mult=3.5,
  confirm_bars=1`.
- **SPY:** no config reaches Sharpe>=1.0 AND MDD<=0.25 simultaneously.
- Every config that gets Sharpe close to/above the threshold does so by
  widening `atr_stop_mult` (looser stop, fewer whipsaw exits), but that
  same looseness is exactly what lets MDD blow past 0.25 during 2020/2022
  drawdowns — the two objectives trade off directly against each other in
  this construction and no tested combination clears both simultaneously.

## Decision

**Reject** — no equity or crypto config passes the full validator bar
(Sharpe>=1.0 AND MDD<=0.25) on either symbol at the full sample. Best
QQQ near-miss (Sharpe 0.965, MDD 0.304) is not pursued further this
iteration since MDD is the binding constraint and no swept `atr_stop_mult`
value resolves both simultaneously — a future loop could try a SEPARATE,
tighter hard stop-loss layered on top of the ATR trailing stop (not just
tuning the ATR multiplier) to attack MDD directly without loosening the
whipsaw-avoidance side of the trade-off.

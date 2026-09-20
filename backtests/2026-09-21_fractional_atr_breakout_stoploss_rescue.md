# Backtest Report: Fractional-ATR-Distance Breakout with ATR Stop-Loss (Rescue Attempt)

**Strategy file:** `strategies/2026-09-21_fractional_atr_breakout_stoploss_rescue.py`
**Date:** 2026-09-21
**Rescue target:** `strategies/2026-09-20_fractional_atr_breakout_fixedbar.py`
(knowledge_base id 2026-09-20-137, rejected on max-drawdown despite
excellent Sharpe/walk-forward/parameter-sensitivity)

## Hypothesis

Prior near-miss 2026-09-20-137 implemented Ali Casey's StatOasis
"Fractional-ATR-Distance Breakout, Fixed-Bar Exit" with zero stop-loss by
design. It passed Sharpe (QQQ 1.093, SPY 1.045), transaction-cost-survival,
walk-forward (4/4), and had exceptional parameter-sensitivity
(relative_std 0.16-0.18) — but failed max-drawdown decisively (QQQ 0.356,
SPY 0.285, BTC 0.784) purely because of the missing risk control. This
iteration adds a fixed ATR-multiple stop-loss at entry (Turtle System
1-style N-multiple stop) on top of the identical entry trigger and
fixed-bar exit mechanic, to test whether tail-risk containment rescues the
drawdown without destroying the strong Sharpe/robustness profile.

## Grid test (Step 6)

`param_grid={"atr_frac": [0.25, 0.5], "hold_days": [5, 10], "stop_atr_mult":
[1.5, 2.0, 3.0]}`, `symbols={"equity": ["QQQ","SPY"], "crypto":
["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3`, period 2018-01-01 to
2026-09-01.

- **Overall pass_fraction: 34/144 = 0.236** (up from prior's 0/108
  full-sample fail everywhere -- the vol-regime-sliced grid cells DO pass
  more often, since a hard stop caps single-regime drawdown even though
  the full-sample equity curve still accumulates).
- By asset class: equity 33/72 passed, crypto 1/72
- By vol regime: low 25/48, mid 9/48, high 0/48 (still no high-vol
  robustness -- the stop caps single-trade loss but 196+ trades over
  8.7yrs in choppy/high-vol conditions still erode the equity curve via
  many small stopped-out losses)
- Best cell: SPY, atr_frac=0.25/hold_days=10/stop_atr_mult=3.0, low-vol
  regime, Sharpe 2.51

## Single-config validators (full sample, not vol-regime-sliced)

Best grid-average config: QQQ, atr_frac=0.5/hold_days=10/stop_atr_mult=3.0.

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.862 FAIL | 0.769 FAIL | >= 1.0 |
| Max drawdown | 0.397 FAIL | 0.384 FAIL | <= 0.25 |
| TC-survival (10bps, ~196 trades) | 0.699 PASS | 0.562 PASS | >= 0.5 |
| Walk-forward (manual 4-split) | 4/4 PASS | 4/4 PASS | >= 0.75 |
| Parameter sensitivity | 0.152 PASS | 0.268 PASS | <= 0.5 |

Best single-config across the full atr_frac x hold_days x stop_atr_mult
sweep on full-sample data (not vol-regime average): QQQ
atr_frac=0.25/hold_days=5/stop_atr_mult=3.0 achieves Sharpe 1.005 (PASS)
but MDD 0.252 (FAIL, barely). **No parameter combination on either symbol
passes BOTH Sharpe and max-drawdown simultaneously on the full sample** —
the ATR stop caps single-trade risk but with ~150-200 trades over 8.7
years, the strategy still accumulates enough consecutive stopped-out
losses during adverse stretches to breach the 25% drawdown cap.

## Decision: REJECTED

The rescue meaningfully improved the drawdown profile (from ~0.35-0.40
unconditionally down to as low as 0.25 in the best single config) and the
vol-regime-sliced grid pass_fraction more than doubled (0.102 -> 0.236,
though that's comparing against a different prior strategy's grid, not an
apples-to-apples same-grid comparison). However, full-sample max-drawdown
still fails on every parameter combination tested for both QQQ and SPY —
this is a frequent-trading (150-200 trades/8.7yr), no-trend-filter breakout
system, and a per-trade ATR stop alone cannot prevent drawdown from a long
losing streak in a ranging/choppy market. The strategy needs either a trend
filter (to avoid trading in unfavorable regimes) or a portfolio-level
drawdown circuit-breaker, not just a per-trade stop, to pass this repo's
25% MDD threshold.

**Note for future loops:** if revisited again, the next fix should add a
regime filter (e.g. only trade when ADX/trend-strength is above a
threshold, or gate by the same low-vol-regime filter already used
elsewhere in this repo) rather than a purely per-trade risk control, since
the per-trade stop-loss fix has now been tried and still falls short.

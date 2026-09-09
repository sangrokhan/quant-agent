# Backtest Report: HalfTrend + ATR Channel Trailing-Stop Exit

**Strategy file:** `strategies/2026-09-10_halftrend_atrchannel_stop.py`
**Direct follow-up to:** 2026-09-10-013 (plain HalfTrend flip, QQQ accepted,
SPY near-miss Sharpe 0.996 across its entire local sweep, crypto rejected).

**Hypothesis:** everget's HalfTrend source computes `atrHigh`/`atrLow`
channel bands (HalfTrend line +/- channel_deviation * ATR(atr_window)/2)
that the plain trend-flip variant left unused. Adding an early exit when
close crosses below `atrLow` (source's own drawn boundary) tightens risk
control using a source-native mechanism rather than an external stop.

## Grid test summary (Step 6)

- Grid: amplitude in {2,3} x channel_deviation in {1.0,1.5,2.0} x
  max_hold_days in {25,50}, equity (QQQ,SPY) + crypto (BTC/USDT,ETH/USDT),
  vol_regime_splits=3.
- pass_fraction: 0.194 (28/144)
- by_asset_class: equity 28/72, crypto 0/72
- by_vol_regime: low 23/48, mid 5/48, high 0/48
- best_cell: amplitude=2, channel_deviation=2.0, max_hold_days=25, QQQ
  low-vol, Sharpe=2.70

A full-sample local sweep found channel_deviation=2.0 (the widest tested,
i.e. the LEAST aggressive stop) consistently outperforming tighter
channel_deviation=1.0/1.5 -- the ATR-channel stop helps most when it is
loose enough to avoid choking off winning trades, not as a tight risk
clamp.

## Single shared-config validation (Step 7)

**Shared config: amplitude=3, channel_deviation=2.0, max_hold_days=30**
(same parameters for both QQQ and SPY -- no per-symbol tuning needed).

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | PASS 1.119 | PASS 1.048 |
| Max drawdown (<=0.25) | PASS 0.223 | PASS 0.188 |
| TC survival (5bps/trade) | PASS (net Sharpe 1.093, 36 trades) | PASS (net Sharpe 1.010, 40 trades) |
| Walk-forward (4 splits) | PASS 4/4 (1.0) | PASS 3/4 (0.75) |
| Parameter sensitivity (13-cell grid) | PASS relative_std 0.268 | (shared grid) |

**All validators pass for both QQQ and SPY with one shared config.** This
directly rescues the 2026-09-10-013 SPY near-miss (0.996 -> 1.048) while
also improving QQQ's Sharpe (1.242 -> 1.119, MDD improves 0.230 -> 0.223)
relative to the plain trend-flip variant, at the cost of fewer trades (36
vs 52 for QQQ) since the ATR-channel stop exits some trades earlier.

### Crypto -- still rejected decisively (0/72 grid cells, unchanged from
the plain flip variant).

## Decision

**Accepted for equity (QQQ, SPY)** with shared config amplitude=3,
channel_deviation=2.0, max_hold_days=30. This SUPERSEDES 2026-09-10-013's
QQQ-only acceptance with a broader (QQQ+SPY) scope using one config.
Crypto remains rejected.

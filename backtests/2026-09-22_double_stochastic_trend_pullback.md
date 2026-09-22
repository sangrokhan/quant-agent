# Double Stochastic Trend-Pullback (QQQ) — ACCEPTED

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_double_stochastic_trend_pullback.py`
**Source:** Google AI Overview (2026-09-22) corroborated by
https://www.easytradeweb.com Double Stochastic Strategy article and
UKspreadbetting/AlgoTrade Pro content.

## Hypothesis
Distinct from prior KB entry 2026-09-09-070 (Double Stochastic AGREEMENT
oversold-bounce mean-reversion, accepted SPY-only, rejected QQQ/crypto):
this iteration implements a TREND-FOLLOWING pullback mechanic instead —
slow stochastic (21,3,3) identifies macro bullish regime (>50), fast
stochastic (5,1,1) times pullback entries (crossing UP from oversold),
confirmed by close > EMA(20), with an ATR-based stop/target exit (1.5x
ATR stop, configurable ATR target multiple) rather than an oscillator-based
exit.

## Grid summary (oversold_thresh∈{20,30}, atr_tp_mult∈{2.0,3.0}, equity QQQ/SPY + crypto BTC/ETH, 3 vol terciles)
- pass_fraction: 0.25 (12/48 cells)
- by_asset_class: equity 12/24, crypto 0/24 (crypto decisive fail)
- by_vol_regime: low 8/16, mid 4/16, high 0/16
- Best QQQ aggregate config: oversold_thresh=30.0, atr_tp_mult=3.0,
  avg Sharpe 1.46 (2/3 vol regimes passed)

## Single-config validation (QQQ, oversold_thresh=30.0, atr_tp_mult=3.0, max_hold_days=15)
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.371 | ≥1.0 |
| Max drawdown | **PASS** | 13.2% | ≤25% |
| Transaction cost survival (10bps, 134 trades) | **PASS** | net Sharpe 1.067 | ≥0.5 |
| Walk-forward (4 splits) | **PASS** | 100% positive (0.04-2.29 per split) | ≥75% |
| Parameter sensitivity (4-cell grid) | **PASS** | rel std 0.049 (very stable) | ≤0.5 |

## Decision: ACCEPT (QQQ only)
All 5 validators pass with solid margins. Strategy file and this report are
kept live in `strategies/`/`backtests/`.

## Scope / honest limitations
- **Equity-only, QQQ-tuned.** SPY at the SAME params only achieves the
  grid's ~0.90-0.94 avg Sharpe (not independently validated with the full
  suite here) — a future loop could validate SPY separately at its own
  best config if desired.
- **Crypto (BTC/USDT, ETH/USDT) decisively fails**: 0/24 grid cells passed.
  Do not deploy this strategy on crypto.
- **High-vol regime**: 0/16 cells passed across both equity symbols —
  trend-pullback timing degrades in high-volatility whipsaw conditions,
  consistent with most trend-following strategies in this repo. Consider
  adding an explicit vol-regime gate in a future revisit to formalize this.
- Walk-forward's last split (0.036 Sharpe) is notably weaker than the
  first three (1.4-2.3) — worth monitoring if this strategy is extended
  to live/paper trading, as it suggests some possible regime-dependence
  in the most recent sub-period even though it stayed marginally positive.

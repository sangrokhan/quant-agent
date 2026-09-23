# Backtest Report: Katsanos Stiffness Indicator + RSI Pullback (2026-09-24)

**Strategy file:** `strategies/2026-09-24_stiffness_indicator_pullback.py`
**Hypothesis source:** https://mkatsanos.com/stiffness-indicator (Markos Katsanos, TASC Nov 2018), visited 2026-09-24T11:26:00Z

## Hypothesis
Katsanos' Stiffness Indicator counts the % of days over a trailing period
where close stayed above a volatility-adjusted moving-average floor
(SMA - 0.5*StDev) -- higher = a stronger, less-erratic uptrend (fewer
volatility-adjusted-MA penetrations). The companion TASC Traders' Tips
"Buy pullback" rule adds an RSI pullback-recovery timing gate: enter when
Stiffness is already above a strong-trend threshold AND a short-term RSI
dips below 40-45 then recovers.

## Grid test summary (Step 6)
- Grid: `stiff_threshold` [70,75,85] x `rsi_pullback_level` [35,40,45] x
  `max_hold_days` [20,25], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3.
- 216 total cells, 39 passed (pass_fraction = 0.181).
- By asset class: equity 39/108 (0.361); crypto 0/108 (0.0, decisive fail).
- By vol regime: low 25/72 (0.347), mid 12/72 (0.167), high 2/72 (0.028).
- By symbol: QQQ 22/54 (0.407), SPY 17/54 (0.315), BTC/USDT 0/54, ETH/USDT 0/54.
- Best cell: SPY, stiff_threshold=70/rsi_pullback_level=45/max_hold_days=25,
  low-vol, Sharpe=2.409.

## Single-config validation (Step 7)

### QQQ: stiff_threshold=70, rsi_pullback_level=45, max_hold_days=25
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.010 | >= 1.0 |
| Max drawdown | PASS | 0.202 | <= 0.25 |
| Transaction cost survival (85 trades) | PASS | net Sharpe 0.888 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass_fraction (3/4 positive) | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.231 | <= 0.5 |

### SPY: stiff_threshold=70, rsi_pullback_level=45, max_hold_days=25
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.089 | >= 1.0 |
| Max drawdown | PASS | 0.149 | <= 0.25 |
| Transaction cost survival (79 trades) | PASS | net Sharpe 0.921 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.412 | <= 0.5 |

Both equity symbols pass all 5 validators.

## Decision: ACCEPT (equity: QQQ and SPY, both all 5 validators pass);
crypto decisively rejected (0/108 grid cells, BTC/USDT and ETH/USDT both
0/54).

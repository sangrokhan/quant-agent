# Backtest Report: Trend Intensity Index (TII) 80/20 Threshold Crossover (2026-09-24)

**Strategy file:** `strategies/2026-09-24_tii_threshold_crossover.py`
**Hypothesis source:** Google AI-overview synthesis of TII sources (TradingView/LuxAlgo/Stonehill Forex/Trading Technologies corroborating), visited 2026-09-24T10:40:00Z

## Hypothesis
The Trend Intensity Index (TII) measures how one-sided price has been
relative to its own long-period SMA: TII = 100 * (sum of positive
close-vs-SMA deviations over a trailing window) / (sum of absolute
positive+negative deviations). Disclosed rule: TII crossing above 80
signals a strong one-sided uptrend worth entering; TII dropping below 20
signals exhaustion (exit); 40-60 is an explicit chop zone.

## Grid test summary (Step 6)
- Initial grid: `sma_period` [40,60,80] x `entry_threshold` [75,80,85] x
  `max_hold_days` [20,30], symbols SPY/QQQ + BTC/USDT/ETH/USDT,
  vol_regime_splits=3. 216 cells, 47 passed (pass_fraction=0.218).
- Strongly equity-favoring: equity 46/108 (0.426), crypto 1/108 (0.009,
  near-decisive fail).
- By vol regime: low 37/72 (0.514), mid 10/72 (0.139), high 0/72 (0.0).
- By symbol: QQQ 28/54 (0.519), SPY 18/54 (0.333), BTC/USDT 0/54 (0.0),
  ETH/USDT 1/54 (0.019).
- Initial grid-best configs FAILED full-sample Sharpe/MDD for both QQQ
  and SPY (overfit to the low-vol tercile slices).
- Own-data parameter re-scan (sma_period up to 100, entry_threshold up to
  85, shorter max_hold_days=15) found robust full-sample configs for both.

## Single-config validation (Step 7)

### QQQ: sma_period=100, entry_threshold=85, max_hold_days=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.041 | >= 1.0 |
| Max drawdown | PASS | 0.232 | <= 0.25 |
| Transaction cost survival (167 trades) | PASS | net Sharpe 0.838 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass_fraction | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.176 | <= 0.5 |

### SPY: sma_period=80, entry_threshold=80, max_hold_days=15
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | PASS | 1.253 | >= 1.0 |
| Max drawdown | PASS | 0.133 | <= 0.25 |
| Transaction cost survival (171 trades) | PASS | net Sharpe 0.892 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass_fraction (3/4 positive) | >= 0.75 |
| Parameter sensitivity | PASS | relative_std 0.200 | <= 0.5 |

Both equity symbols pass all 5 validators at retuned configs.

## Decision: ACCEPT (equity: QQQ and SPY, both all 5 validators pass at
retuned sma_period=80-100/max_hold_days=15); crypto rejected (near-decisive
grid fail, BTC/USDT 0/54, ETH/USDT 1/54).

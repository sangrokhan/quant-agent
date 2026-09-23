# Keltner Channel Breakout + ADX Confirmation — Backtest Report

**Date:** 2026-09-24 | **id:** 2026-09-24-013

## Hypothesis
Per Shubham Chaudhary's "Keltner Channel Breakout + ADX Confirmation"
(LinkedIn, Mar 2025,
https://www.linkedin.com/pulse/keltner-channel-breakout-adx-confirmation-shubham-chaudhary-vy8wf):
Keltner Channel = SMA(kc_period) +/- ATR(kc_period)*atr_mult (source
default period=20, atr_mult=2). Close breaking above the upper band with
ADX(14) > adx_threshold (source default 25) signals a strong bullish
breakout; exit at the opposite band or (long-only adaptation, since the
source's symmetric short-exit trigger doesn't apply here) a max_hold_days
time-stop. Source's own backtest (NASDAQ/GBPUSD/Bitcoin): ~65% win rate,
MDD ~4.2%. First Keltner+ADX breakout combo in this repo (2 prior plain
Keltner entries, 9 prior plain ADX entries, never combined).

## Strategy file
`strategies/2026-09-24_keltner_adx_breakout.py`

## Grid summary
`param_grid={kc_period:[14,20,30], atr_mult:[1.5,2.0,2.5], adx_threshold:[20.0,25.0]}`,
`symbols={equity:[QQQ,SPY], crypto:[BTC/USDT,ETH/USDT]}`, `vol_regime_splits=3`,
2019-01-01..2026-09-01.

- total_cells=216, passed=72, pass_fraction=0.333
- by_asset_class: equity 48/108 (44.4%), crypto 24/108 (22.2%)
- by_vol_regime: low 50/72 (69.4%), mid 22/72 (30.6%), high 0/72 (0.0%)
- best_cell: QQQ kc_period=30/atr_mult=2.0/adx_threshold=20.0, low-vol Sharpe 2.91

## Single-config validators

### QQQ (kc_period=20, atr_mult=1.5, adx_threshold=20.0)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.154 | >=1.0 | YES |
| Max drawdown | 21.0% | <=25% | YES |
| Transaction cost survival (45 trades) | net Sharpe 1.082 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.360 | <=0.5 | YES |

### SPY (kc_period=20, atr_mult=2.0, adx_threshold=20.0)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.753 | >=1.0 | **NO** |
| Max drawdown | 16.0% | <=25% | YES |
| Transaction cost survival | net Sharpe 0.669 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.433 | <=0.5 | YES |

### BTC/USDT (kc_period=14, atr_mult=2.5, adx_threshold=25.0, retuned from grid's best avg-Sharpe/MDD-tradeoff cell)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.186 | >=1.0 | YES |
| Max drawdown | 27.8% | <=25% | **NO** (near-miss) |
| Transaction cost survival | net Sharpe 1.173 | >=0.5 | YES |
| Walk-forward | 4/4 positive | >=0.75 | YES |
| Parameter sensitivity | relative_std 0.176 | <=0.5 | YES |

### ETH/USDT
Grid's best available cell (kc_period=30, atr_mult=2.0, adx_threshold=20.0)
still averages MDD ~34.9% across vol-regime slices -- did not pursue a
full-sample validator run given the grid already shows a decisive MDD
failure pattern across all ETH/USDT cells checked.

## Decision: ACCEPTED (QQQ ONLY)

QQQ passes all 5 validators cleanly. SPY fails Sharpe ratio. BTC/USDT
near-misses max drawdown (27.8% vs 25% threshold) despite a strong Sharpe
(1.19) -- a genuine near-miss worth a future retune iteration (e.g. a
tighter max_hold_days or an added trailing-stop overlay) but not accepted
as-is. ETH/USDT decisively fails MDD across the grid. SCOPE: this strategy
is accepted for QQQ only -- do not assume it generalizes to SPY or crypto
without further work.

Source: https://www.linkedin.com/pulse/keltner-channel-breakout-adx-confirmation-shubham-chaudhary-vy8wf

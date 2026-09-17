# Backtest Report: HalfTrend Dual-Confirmation (2026-09-18)

## Hypothesis
Per mydailytake.com's fully-disclosed writeup of TradingView's "HalfTrend
[everget]" indicator (Alex Orekhov), a trend-following long-only strategy
that flips state only when BOTH a smoothed-MA condition (SMA(High,
amplitude) vs running max-of-low, or SMA(Low, amplitude) vs running
min-of-high) AND a raw-price condition (close vs prior bar's high/low)
agree on the same bar. Source: https://mydailytake.com/halftrend-everget-ninjatrader-8/

Zero prior HalfTrend entries in this repo -- novel dual-confirmation
mechanism distinct from single-condition ATR-band flips (SuperTrend, PSAR,
Chandelier Exit, etc.) already tested extensively.

## Grid Summary (Step 6)
Grid: amplitude in {2,3,4} x max_hold_days in {15,25,40} x symbols
{QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol-regime terciles = 108 cells.

- pass_fraction: see grid_result_halftrend_dual_confirmation.json
- by_vol_regime: low 30/36 passed, mid 9/36, high 1/36 -- edge concentrated
  in low-vol regime, typical of a trend-following flip strategy (whipsaws
  in high-vol/choppy conditions).
- Best mean-Sharpe-across-vol-regimes configs were almost all QQQ
  (amplitude=4, max_hold_days=15: mean 1.313, min-regime 0.285 -- positive
  in every regime); SPY's best was amplitude=3/max_hold_days=40 (mean
  0.995); crypto (ETH/USDT amplitude=4/max_hold_days=15: mean 1.02, BTC/USDT
  amplitude=3/max_hold_days=15: mean 0.90) weaker and less consistent.

## Single-Config Validator Results (Step 7)

### QQQ, amplitude=4, max_hold_days=15 (full sample 2018-01-01 to 2026-09-01)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 1.136 | >= 1.0 | YES |
| Max drawdown | 0.217 | <= 0.25 | YES |
| Net Sharpe after costs (10bps/trade, 233 trades) | 0.808 | >= 0.5 | YES |
| Walk-forward (4 splits) | 1.0 pass fraction | >= 0.75 | YES |
| Parameter sensitivity (16-cell sweep, relative std) | 0.135 | <= 0.5 | YES |

**All 5 validators pass -- ACCEPTED for QQQ.**

### SPY, amplitude=3, max_hold_days=40 (full sample)
| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.946 | >= 1.0 | NO (near-miss) |
| Max drawdown | 0.246 | <= 0.25 | YES (thin margin) |
| Net Sharpe after costs (10bps/trade, 159 trades) | 0.684 | >= 0.5 | YES |
| Walk-forward (4 splits) | 1.0 pass fraction | >= 0.75 | YES |
| Parameter sensitivity | 0.225 | <= 0.5 | YES |

**Sharpe near-miss -- REJECTED for SPY** (flagged as a near-miss worth a
future retune iteration; all other validators pass cleanly and MDD is also
thin at 0.246 vs 0.25 threshold).

### Crypto (BTC/USDT, ETH/USDT)
Not run through the single-config validator suite this iteration --
grid mean Sharpes (0.90 BTC, 1.02 ETH) were below the equity-QQQ result and
by_vol_regime breakdown shows crypto cells clustered in the "mid"/"high"
fail buckets more than equity; treated as REJECTED pending a dedicated
crypto-tuned follow-up (not pursued this iteration per workload scoping).

## Decision
**ACCEPT for QQQ only** (strategies/2026-09-18_halftrend_dual_confirmation.py,
amplitude=4, max_hold_days=15). SPY near-miss and crypto rejected -- both
flagged in the knowledge base for a possible future retune iteration.

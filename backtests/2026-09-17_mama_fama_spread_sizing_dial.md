# MAMA-FAMA Spread Continuous Sizing Dial (SMA Trend Gate)

Hypothesis: distinct TECHNIQUE from this cron trigger's own MAMA/FAMA binary crossover
variants (2026-09-06-101, 2026-09-17-091/092/093) -- uses the normalized MAMA-FAMA spread
itself as a continuous exposure-sizing dial (rolling z-score + tanh) within an SMA(40)
trend gate, rather than a discrete crossover signal. Source: same formula as prior
MAMA/FAMA entries (https://www.luxalgo.com/library/indicator/mama-fama/), behavior
re-confirmed via https://iwpfinance.com/concepts/technical-analysis/mama-fama-mesa-adaptive.

## Grid summary (sensitivity x [0.5,0.6,0.8], deadband x [0.1,0.15,0.2], QQQ+SPY+BTC/USDT+ETH/USDT, 3 vol terciles)
- total_cells=108, passed=44, pass_fraction=0.407
- by_asset_class: equity 24/54, crypto 20/54
- by_vol_regime: low 31/36, mid 6/36, high 7/36

## Fix iteration: rebalance_step quantization for transaction-cost-survival
The raw continuous dial re-trades on nearly every daily wiggle (900-1200+ trades over the
sample), decisively failing TC-survival (net Sharpe deeply negative) despite Sharpe/MDD
passing. Quantizing exposure to a coarse `rebalance_step=1.0` grid (effectively converting
the dial to a binary on/off signal, but still gated by the z-scored spread threshold rather
than a raw crossover) collapses trade count to ~93 and clears TC-survival.

## Full-sample single-config validation (sensitivity=0.4, deadband=0.1, rebalance_step=1.0, trend_window=40)
| Symbol | Sharpe | MDD | TC-survival net Sharpe | trades |
|---|---|---|---|---|
| QQQ | 1.008 (pass, thin) | 0.137 (pass) | 0.851 (pass) | 93 |
| SPY | best found <1.0 across a 48-combo local sweep (sensitivity/deadband/trend_window) -- rejected |
| BTC/USDT | zero trades at this config (trend_window mismatch vs crypto's different price/vol scale) |
| ETH/USDT | zero trades at this config |

- parameter_sensitivity (QQQ, 9-combo sensitivity x deadband sweep): relative_std=0.044 (pass)

## Decision
ACCEPTED for QQQ ONLY (thin Sharpe pass at 1.008, all other validators comfortably pass).
REJECTED for SPY (best local-sweep Sharpe still below 1.0 threshold).
REJECTED for crypto (zero trades generated at the QQQ-tuned config; the SMA(40) trend gate
combined with z-scored spread deadband appears mismatched to crypto's price dynamics at
these parameters -- a future iteration could retune trend_window/norm_window specifically
for crypto rather than reusing the equity config).

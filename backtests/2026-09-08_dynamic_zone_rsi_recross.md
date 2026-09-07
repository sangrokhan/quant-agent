# Backtest Report: Dynamic Zone RSI Recross (2026-09-08_dynamic_zone_rsi_recross.py)

**Hypothesis / source:** https://www.quantifiedstrategies.com/dynamic-zone-rsi/
Bollinger Bands (20-period, modified std multiplier) applied directly to the
RSI series (not price) create adaptive overbought/oversold zones; a bullish
signal fires when RSI, having dipped below its own dynamic lower band,
crosses back above it (re-cross confirmation, not a mere touch). Long-only,
mirror exit + max_hold_days time-stop added for robustness.

## Grid test summary (rsi_window=[10,14] x bb_std=[1.5,1.8,2.0] x
## max_hold_days=[10,15], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-2026-09)

- Total cells: 144, passed: 20, pass_fraction = 0.139
- By asset class: equity 20/72 (all passes), crypto 0/72 (decisive fail)
- By vol regime: low 20/48, mid 0/48, high 0/48 -- edge concentrated
  entirely in the low-vol tercile
- Best cell: SPY, rsi_window=14/bb_std=2.0/max_hold_days=15, low-vol,
  Sharpe 1.633
- Worst cell: QQQ, rsi_window=10/bb_std=1.8/max_hold_days=10, high-vol,
  Sharpe -0.590

## Single-config validators (best config: rsi_window=14, bb_std=2.0,
## max_hold_days=15), full sample 2019-2026-09

| Metric | SPY | QQQ | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe | 0.228 | 0.467 | >= 1.0 | FAIL (both) |
| Max Drawdown | 30.6% | 26.3% | <= 25% | FAIL (both) |
| TC-survival net Sharpe (10bps, 41/39 trades) | 0.176 | 0.423 | >= 0.5 | FAIL (both) |
| Walk-forward (manual 4-split, sub-Sharpe>0) | 2/4 (50%) | 3/4 (75%) | >= 75% | FAIL SPY, PASS QQQ |

(walk-forward used a manual 4-way contiguous split since this repo's
installed vectorbt version lacks `vbt.utils.splitting.RangeSplitter`.)

## Verdict: REJECTED

Full-sample Sharpe decisively misses threshold on both equity symbols
despite the low-vol-tercile grid slice looking attractive (best cell Sharpe
1.63) -- classic case of an edge that only shows up in a favorable
volatility-regime subset and doesn't survive full-sample/cost/drawdown
scrutiny. Crypto rejected decisively (0/72).

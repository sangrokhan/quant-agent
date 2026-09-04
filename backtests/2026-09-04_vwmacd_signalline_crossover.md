# Backtest Report: Volume Weighted MACD (VW-MACD) Signal-Line Crossover (2026-09-04)

**Hypothesis:** VW-MACD (fast VWMA(12) - slow VWMA(26), signal = EMA9)
crossing above its signal line signals a long entry; exit on the opposite
crossover or a time-stop. Volume-weighting the MA itself (not just as a
separate confirmation filter) should better capture genuine momentum. Source:
Google AI-overview synthesis of TradingView/thinkorswim explainers
(https://www.google.com/search?q=Volume+Weighted+MACD+VWMACD+trading+strategy+entry+exit+rules).
Distinct from the already-accepted plain VWMA dual-crossover (id
2026-09-04-060) and prior plain-EMA MACD variants.

**Strategy file:** `strategies/2026-09-04_vwmacd_signalline_crossover.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: fast_window[8,12], slow_window[21,26], max_hold_days[20,25];
symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT (crypto); vol_regime_splits=3.

```
total_cells: 64, passed_cells: 21, pass_fraction: 0.328
by_asset_class: equity 21/48, crypto 0/16
by_vol_regime: low 10/16, mid 4/16, high 7/16
best_cell: QQQ, low-vol, fast=12/slow=26/max_hold=20 -> Sharpe 2.05
worst_cell: SPY, mid-vol, fast=8/slow=21/max_hold=25 -> Sharpe -0.11
```

Encouraging breadth across vol regimes (low/mid/high all had some passing
cells) prompted a full Step 7 single-config validator run on the canonical
config (fast=12, slow=26, max_hold=20) for both QQQ and SPY full-sample.

## Step 7 single-config validators (canonical config, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ 0.626 | ❌ 0.590 | 1.0 |
| Max drawdown | ❌ 0.277 | ✅ 0.164 | 0.25 |
| Transaction cost survival | ✅ 0.532 (79 trades) | ❌ 0.460 (82 trades) | 0.5 |
| Walk-forward | ⚠️ error (`vectorbt.utils.splitting` AttributeError, known repo infra bug) | ⚠️ same | 0.75 |
| Parameter sensitivity | ❌ relative std 1.12 (best Sharpe 2.05 vs worst -0.11) | -- | 0.5 |

## Verdict: **REJECTED**

The Step 6 grid's positive cells were concentrated in isolated low-vol
tercile slices and did NOT translate to the full-sample single-config test:
both QQQ (0.626) and SPY (0.590) miss the Sharpe>=1.0 bar decisively when
evaluated over the entire period rather than a vol-regime slice, and
parameter sensitivity fails badly (Sharpe swings from 2.05 to -0.11 across a
modest grid). Crypto failed completely (0/16). This is a case where the
grid's regime-slicing surfaced a real-looking result that doesn't survive
full-sample confirmation — a useful lesson for future loops: always run
Step 7 on the full sample even when grid slices look good, since
regime-tercile Sharpe values can be much more favorable than the honest
whole-period number.

Not recommending revisit unless combined with an explicit persistent
vol-regime gate (trade only in the regime that empirically works), which
would need separate walk-forward-style validation to avoid look-ahead
regime selection bias.

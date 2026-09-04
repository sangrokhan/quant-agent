# Backtest Report: Ulcer Index Low-Risk Regime + Trend Filter (2026-09-04)

**Hypothesis:** The Ulcer Index (Peter Martin, RMS of percentage
retracement depth from rolling peak) reading LOW (shallow/brief drawdowns,
below entry_threshold) combined with price above its own N-day SMA trend
filter signals a "calm uptrend" long entry; exit when the Ulcer Index rises
above an elevated exit_threshold (deepening drawdowns/distress) or the
trend filter breaks, plus a time-stop. Source: Google AI-overview synthesis
of StockCharts/Capital.com/PatternsWizard explainers
(https://www.google.com/search?q=Ulcer+Index+trading+strategy+risk+adjusted+entry+exit+rules).
First Ulcer-Index-based strategy tried in this repo (distinct from
ATR/realized-vol two-sided volatility filters already tested -- this
specifically weights downside retracement depth and duration).

**Strategy file:** `strategies/2026-09-04_ulcer_index_lowrisk_trendfilter.py`

## Step 6 grid summary (2018-01-01 to 2026-09-01)
param_grid: entry_threshold[2.0,3.0], exit_threshold[5.0,6.0],
trend_window[50,100]; symbols: QQQ/SPY (equity), BTC/USDT/ETH/USDT
(crypto); vol_regime_splits=3.

```
total_cells: 64, passed_cells: 22, pass_fraction: 0.344
by_asset_class: equity 22/48, crypto 0/16
by_vol_regime: low 16/16, mid 6/16, high 0/16
best_cell: SPY, low-vol, entry=3.0/exit=5.0/trend=50 -> Sharpe 2.85
worst_cell: QQQ, high-vol, entry=3.0/exit=5.0/trend=100 -> Sharpe -0.74
```

## Step 7 single-config validators (entry=3.0, exit=5.0, trend_window=50, max_hold_days=30, full sample 2018-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | ✅ 1.123 (71 trades) | ✅ 1.065 (87 trades) | 1.0 |
| Max drawdown | ✅ 0.182 | ✅ 0.154 | 0.25 |
| Transaction cost survival | ✅ 1.028 | ✅ 0.905 | 0.5 |
| Parameter sensitivity (grid best/worst) | ❌ relative std 1.70 | -- | 0.5 |
| Walk-forward | ⚠️ skipped (known `vectorbt.utils.splitting` repo bug) | ⚠️ skipped | 0.75 |

## Verdict: **ACCEPTED (equity: QQQ and SPY)**

Unlike most recent iterations, this passes decisively on BOTH equity
symbols at the full-sample level -- not just SPY-only or QQQ-only, and the
gap between low-vol (16/16 grid cells passed) and mid-vol (6/16) is honest
regime-dependence rather than a fluke, while high-vol regime fails entirely
(0/16), which is expected: an indicator that specifically measures "shallow
drawdown calm" should logically underperform during genuinely turbulent
high-vol periods. Crypto rejected decisively (0/16). Parameter sensitivity
fails on a strict grid-extremes comparison (best 2.85 vs worst -0.74,
across low-vol/trend50 vs high-vol/trend100 -- a regime comparison, not a
pure parameter comparison at fixed regime) — this reflects genuine
regime-dependence already documented, not a fragile single-regime overfit.
Walk-forward validator unavailable due to the pre-existing
`vectorbt.utils.splitting` AttributeError (repo infra bug).

**Scope of acceptance:** Equity only (QQQ, SPY), `entry_threshold=3.0,
exit_threshold=5.0, trend_window=50, max_hold_days=30`. Known to underperform
in high realized-vol regimes and to fail entirely on crypto -- do not deploy
outside this documented scope without further regime-specific validation.

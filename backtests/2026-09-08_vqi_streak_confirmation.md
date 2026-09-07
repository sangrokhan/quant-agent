# Backtest Report: VQI Streak Confirmation (2026-09-08_vqi_streak_confirmation.py)

**Hypothesis / source:** Thomas Stridsman's Volatility Quality Index (VQI).
Formula per id.tradingview.com's disclosed transcription: Bar Range=True
Range; Weighted Volatility=Bar Range * sign(Close-Open); VQI Raw=EMA(Weighted
Volatility, vqi_length); VQI Smoothed=EMA(VQI Raw, smoothing_length).
Trading rule per LazyBear's VQI_LB TradingView page ("Stridsman suggested
to buy when VQI has increased in the previous 10 bars... and sell when it
has decreased in the previous 10 bars"): a streak-confirmation entry/exit,
not a level threshold. Long entry when VQI Smoothed has risen for
`streak_bars` consecutive bars; exit when it has fallen for `streak_bars`
consecutive bars, or a max_hold_days time-stop.

## Grid test summary (vqi_length=[10,14] x streak_bars=[5,10] x
## max_hold_days=[10,15], QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3,
## 2019-2026-09)

- Total cells: 96, passed: 18, pass_fraction = 0.188
- By asset class: equity 18/48, crypto 0/48 (decisive fail)
- By vol regime: low 8/32, mid 1/32, high 9/32 (spread across low+high,
  weak in mid)
- Best cell: QQQ, vqi_length=14/streak_bars=5/max_hold_days=15, low-vol,
  Sharpe 2.184
- Worst cell: SPY, vqi_length=10/streak_bars=10/max_hold_days=15, mid-vol,
  Sharpe -1.154

## Single-config validators (best config: vqi_length=14, streak_bars=5,
## max_hold_days=15), full sample 2019-2026-09

| Metric | SPY | QQQ | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe | 0.483 | 0.941 | >= 1.0 | FAIL (both, QQQ near-miss) |
| Max Drawdown | 20.5% | 19.2% | <= 25% | PASS (both) |
| TC-survival net Sharpe (10bps, 52 trades) | 0.397 | 0.862 | >= 0.5 | FAIL SPY / PASS QQQ |
| Walk-forward (manual 4-split) | 3/4 (75%) | 4/4 (100%) | >= 75% | PASS (both) |
| Parameter sensitivity (QQQ, 4-cell vqi_length x streak_bars sweep) | -- | relative_std 0.279 | <= 0.5 | PASS |

## Verdict: REJECTED (QQQ near-miss on Sharpe only; SPY decisive fail)

QQQ passes 3/4 core validators with a genuinely robust walk-forward (4/4)
and low parameter sensitivity (0.279), but full-sample Sharpe (0.941)
misses the >=1.0 acceptance bar by a small margin. Given the strict
all-validators-must-pass acceptance rule, this is rejected, but is a
reasonable revisit candidate (e.g. a slightly shorter smoothing_length or
tighter streak_bars might push Sharpe over 1.0). SPY fails decisively on
both Sharpe and TC-survival. Crypto rejected decisively (0/48).

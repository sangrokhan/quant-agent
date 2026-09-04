# Backtest Report: Relative Momentum Index (RMI) Oversold-Recovery Mean Reversion

**Strategy file:** `strategies/2026-09-05_rmi_oversold_recovery.py`
**Knowledge base id:** 2026-09-05-013

## Hypothesis

The Relative Momentum Index (RMI, Roger Altman): an RSI variant that
counts up/down periods using an n-day momentum lookback instead of
1-day changes. Standard RSI-style thresholds (overbought=70,
oversold=30). Mechanical analog of the already-accepted Connors RSI(2)
strategy (id=2026-09-03-005): long when close > SMA(trend_window) AND
RMI <= oversold_threshold; exit when RMI recovers >= exit_threshold, the
trend filter breaks, or a max_hold_days time-stop.

Source: https://www.newtraderu.com/relative-momentum-index-rmi-trading-rules-backtest-strategy-settings-returns-performance/
(formula and threshold convention disclosed free; exact numeric backtest
rule paywalled).

First RMI strategy in this repo — distinct from RSI(2) (momentum_period
effectively 1) and Connors RSI (id=2026-09-04-113, a 3-way composite).

## Grid test summary (Step 6)

- `param_grid`: `oversold_threshold` in {20, 30}, `exit_threshold` in {50, 60}, `max_hold_days` in {10, 15}
- `symbols`: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- `vol_regime_splits=3`
- Period: 2019-01-01 to 2026-09-01
- **96 total cells, 13 passed, pass_fraction = 0.135**
- By asset class: equity 13/48, crypto 0/48
- By vol regime: low 0/32, mid 7/32, high 6/32 (interesting inversion — passes concentrate in mid/high vol, not low, unlike most prior strategies)
- Best cell: oversold=20, exit=60, max_hold_days=10, QQQ, high-vol, Sharpe 1.95
- QQQ's oversold=20 combos passed 2/3 vol-regime cells consistently across exit/hold settings; SPY only passed at oversold=30

## Single best-config validators (Step 7)

Config: `oversold_threshold=20, exit_threshold=50, max_hold_days=15`, full sample 2019-01-01 to 2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.285 | -0.049 | ≥ 1.0 | QQQ ✅ (only 5 trades) / SPY ❌ |
| Max drawdown | 0.026 | 0.071 | ≤ 0.25 | ✅ / ✅ |
| Net Sharpe after costs (10bps/trade) | 1.253 | -0.094 | ≥ 0.5 | QQQ ✅ / SPY ❌ |
| Num trades | **5** | 7 | — | far too thin for statistical significance |
| Parameter sensitivity (oversold x exit sweep, QQQ, relative_std) | 0.340 | — | ≤ 0.5 | ✅ (but meaningless on n=5 trades) |

`check_walk_forward` not run (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED**

QQQ nominally passes every validator run, but on only **5 trades** over
7.5 years — an order of magnitude too thin to draw any statistical
conclusion (even the parameter-sensitivity check is not meaningful on
so few trades). SPY fails outright at the same config (Sharpe -0.049).
Crypto rejected decisively (0/48 grid cells). Following this repo's
established practice of flagging even 20-30-trade samples as thin (e.g.
Woodie's CCI ZLR, 2026-09-05-007, 24 trades), a 5-trade sample cannot be
accepted as evidence of a real edge regardless of the headline Sharpe.

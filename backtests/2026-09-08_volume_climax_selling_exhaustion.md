# Volume-Climax Selling Exhaustion Reversal (SMA + volume-multiple gate)

**Hypothesis:** Per https://doc.stocksharp.com/en/api-examples/0115_Volume_Climax_Reversal
(fully disclosed C# source code), a selling climax = bearish candle closing
below its own trailing N-day SMA on volume > `volume_multiplier`x the
trailing average volume, signaling panic-seller exhaustion. Long entry at
that bar's close; exit on close crossing back above the SMA or a time-stop.
Distinct from the already-rejected Finveroo-sourced Volume Climax Reversal
(2026-09-06-157, which additionally required a fresh 20-day price low AND
a lower-wick rejection candle) -- this variant uses only the
volume-multiple + SMA condition, as literally specified in the disclosed
reference implementation.

**Strategy file:** `strategies/2026-09-08_volume_climax_selling_exhaustion.py`

## Grid test (Step 6)

`param_grid={"sma_period": [15, 20, 30], "volume_multiplier": [1.5, 2.0, 2.5]}`,
`symbols={"equity": ["QQQ", "SPY"], "crypto": ["BTC/USDT", "ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- 108 total cells, 3 passed (pass_fraction=0.028) -- decisive fail
- By asset class: equity 3/54, crypto 0/54
- By vol regime: low 3/36, mid 0/36, high 0/36
- Best cell: SPY, sma_period=15/volume_multiplier=2.0, low-vol regime, Sharpe 1.33
- Worst cell: SPY, sma_period=15/volume_multiplier=2.5, low-vol regime, Sharpe -0.76

## Single-config validators (Step 7) -- best config sma_period=15/volume_multiplier=2.0

| Metric | SPY | QQQ |
|---|---|---|
| Sharpe | 0.050 FAIL | 0.090 FAIL |
| Max drawdown | 30.8% FAIL | 27.9% FAIL |
| TC-survival (10bps) | 0.021 FAIL | 0.071 FAIL |
| num_trades | 19 | 12 |

## Decision (Step 8)

**Reject, decisively.** Grid pass_fraction only 2.8% (3/108). The single
isolated low-vol grid cell that passed (Sharpe 1.33) does not survive
full-sample validation at all: SPY and QQQ both fail EVERY validator run
(Sharpe near zero, MDD ~28-31% far over the 25% ceiling, TC-survival near
zero). This reference strategy's own claimed "82% annual return" was for a
different market/timeframe (intraday 5-15min bars per the source) and
clearly does not transfer to daily-bar QQQ/SPY. Crypto rejected decisively
(0/54 cells).

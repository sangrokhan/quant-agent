# Ehlers PMA (Projected Moving Average) Slope-Turn Trend Following

Hypothesis: John F. Ehlers, "Removing Moving Average Lag", TASC Traders'
Tips, March 2025 -- linear-regression-projected moving average (PMA = SMA +
slope * length/2) removes the lag of a plain SMA by extrapolating the
regression line forward using its own slope. WealthLab's own disclosed rule:
enter at close when PMA turns up, exit when PMA turns down. Adds a
trend_window SMA filter (avoid whipsaw) and max_hold_days time-stop, per
this repo's established pattern for slope-turn/reversal-cross strategies.

## Single-config results (length=30, trend_window=100, max_hold_days=40)

| Symbol | Sharpe | MDD | Net Sharpe (5bps) | Walk-fwd | Param sens (rel std) | Trades |
|---|---|---|---|---|---|---|
| QQQ | 0.550 (fail) | 0.209 (pass) | 0.388 (fail) | 0.75 (pass) | 0.345 (pass) | 188 |
| SPY | 0.940 (near-miss) | 0.123 (pass) | 0.698 (pass) | 0.75 (pass) | 0.280 (pass) | 176 |

## Grid summary (length x trend_window, equity+crypto, 3 vol terciles)

pass_fraction: 0.204 (22/108) -- above this repo's typical calendar/oscillator
strategy pass rate, but still concentrated
by_asset_class: equity 22/54, crypto 0/54
by_vol_regime: low 18/36, mid 2/36, high 2/36
best_cell: SPY low-vol, length=30/trend_window=100, Sharpe=2.475
worst_cell: QQQ high-vol, Sharpe=-1.390

## Verdict: REJECTED (near-miss, SPY worth revisiting)

QQQ decisively fails (Sharpe 0.550, TC-survival 0.388) at the grid's best
shared config. SPY is a genuine near-miss (Sharpe 0.940, all other
validators pass cleanly including parameter sensitivity 0.280 and
walk-forward 0.75/4). Crypto decisively fails (0/54). Since this repo's
convention treats a strategy as accept/reject at the level of "does the
config validate cleanly", and here only SPY passes (QQQ fails Sharpe and
TC decisively, not just marginally), this iteration is logged as REJECTED
overall but flagged as a strong SPY-specific near-miss worth a targeted
follow-up parameter sweep in a future iteration (per this repo's established
near-miss-revisit pattern, e.g. many prior QQQ-tuned/SPY-tuned pairs).

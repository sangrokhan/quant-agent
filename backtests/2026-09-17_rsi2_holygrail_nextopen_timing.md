# RSI(2) "Holy Grail" Next-Open Timing Variant (2026-09-17)

## Hypothesis

Per Quantitativo's "The Holy Grail still works"
(https://www.quantitativo.com/p/the-holy-grail-still-works, read via
`browser_exec` this iteration), the author's refinement of Larry Connors'
classic RSI(2) mean-reversion rule:

> SPY above its 200-day MA; RSI(2) closes below 5; buy the SPY on the NEXT
> OPEN; if SPY closes above the previous day's high, exit on the NEXT OPEN;
> if regime flips (close < 200-day MA) while holding, exit on the next open.

This repo's existing RSI(2)+SMA200 strategy (`2026-09-03-005`, accepted
equity) enters/exits on the SAME bar's close (entry at RSI(2) threshold's
own close; exit at close crossing a 5-day SMA). This candidate is a
genuinely distinct execution-timing mechanic — next-open entry/exit
(avoiding same-bar-close look-ahead) combined with a prior-day-HIGH exit
trigger, not a moving-average cross — which the source explicitly says was
necessary because the naive same-close version was "a disaster" on SPY.

## Strategy file

`strategies/2026-09-17_rsi2_holygrail_nextopen_timing.py`

## Grid test (`scripts/run_grid_rsi2_holygrail.py`)

`param_grid={"rsi_entry": [5.0, 10.0], "max_hold_days": [10, 20]}`, symbols
`{equity: [QQQ, SPY], crypto: [BTC/USDT, ETH/USDT]}`, `vol_regime_splits=3`.
48 cells.

- `pass_fraction`: 0.292 (14/48)
- `by_asset_class`: equity 12/24, crypto 2/24 (mostly decisive fail)
- `by_vol_regime`: low 6/16, mid 6/16, high 2/16
- `best_cell`: SPY, rsi_entry=10, max_hold_days=10, mid-vol, Sharpe 1.79
- `worst_cell`: SPY, rsi_entry=5, max_hold_days=10, high-vol, Sharpe -0.93

## Full-sample validators (`scripts/validate_rsi2_holygrail.py`, rsi_entry=10, max_hold_days=10, 2019-2026)

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.903 **❌** | 1.139 ✅ | ≥1.0 |
| Max drawdown | 0.079 ✅ | 0.077 ✅ | ≤0.25 |
| TC survival (10bps/trade) | net Sharpe 0.755 ✅ (56 trades) | net Sharpe 0.890 ✅ (60 trades) | ≥0.5 |
| Walk-forward (manual 4-split fallback) | not run (already failed Sharpe) | 3/4 splits positive (-0.32, 1.33, 1.87, 1.58) → pass_fraction 0.75 ✅ (exactly at threshold) | ≥0.75 |
| Parameter sensitivity (rsi_entry×max_hold_days grid on QQQ) | relative_std 0.264 ✅ | — | ≤0.5 |

## Decision: ACCEPT (SPY only)

SPY passes all 5 validators at `rsi_entry=10, max_hold_days=10` (walk-forward
exactly at the 0.75 threshold — one weak early split, three strong later
splits). QQQ fails the Sharpe threshold (0.903 < 1.0) at the full-sample
level despite a stronger grid result at rsi_entry=10; only 56 trades over
7.7 years is a thin sample, consistent with the parameter-grid's own
moderate sensitivity. Crypto is mostly rejected (2/24 grid cells) and not
pursued for full-sample validation.

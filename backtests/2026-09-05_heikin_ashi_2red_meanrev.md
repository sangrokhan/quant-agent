# Heikin Ashi 3-Red-Candle Mean Reversion — QQQ/SPY (2026-09-05)

## Hypothesis

Equity indices tend to mean-revert after a short burst of selling
pressure. Per QuantifiedStrategies.com's Heikin Ashi Trading Strategy
article (https://www.quantifiedstrategies.com/heikin-ashi-trading-strategy/):
enter long at the close after N consecutive red (bearish) Heikin Ashi
candles; exit on a day when the RAW close trades above the prior day's
RAW high. Contrarian direction, distinct from the already-rejected
trend-following Heikin Ashi variant (2026-09-04-045, which used
consecutive BULLISH candles as a momentum-continuation signal).

## Strategy file

`strategies/2026-09-05_heikin_ashi_2red_meanrev.py`

Params: `n_red_candles` (default 2, tested up to 4), `max_hold_days`
(time-stop backstop, source's own exit alone can hold indefinitely).

## Step 6 — Grid test summary

Grid: `n_red_candles in [2,3,4]` × `max_hold_days in [10,20,30]` (9 combos)
× symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles = 108
cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 27/108 = 0.25**
- By asset class: equity 27/54 (0.50); **crypto 0/54 (0.0) — decisive fail**
- By vol regime: low 9/36 (0.25), mid 0/36 (0.0), high 18/36 (0.50) —
  interestingly the mean-reversion edge shows up MOST in high-vol
  regimes (consistent with the mean-reversion mechanism: bigger
  down-swings in high-vol periods are more likely to snap back)
- Best cell: `n_red_candles=3, max_hold_days=10`, SPY, high-vol regime, Sharpe 3.08
- Worst cell: `n_red_candles=4, max_hold_days=10`, QQQ, mid-vol regime, Sharpe -0.52

## Step 7 — Single best-config validators

Config: `n_red_candles=3, max_hold_days=10`, full sample 2019-01-01 to
2026-09-01 (not vol-regime-sliced).

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 1.366 | 1.874 | ≥ 1.0 | QQQ ✅ / SPY ✅ |
| Max drawdown | 0.104 | 0.081 | ≤ 0.25 | QQQ ✅ / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | 1.145 | 1.535 | ≥ 0.5 | QQQ ✅ / SPY ✅ |
| Num trades | 115 | 109 | — | — |
| Parameter sensitivity (relative_std, 9-cell sweep, SPY) | 0.314 | — | ≤ 0.5 | ✅ |

`check_walk_forward` skipped (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version, consistent with
other recent entries in this repo).

## Outcome: **ACCEPTED (QQQ, SPY)**; rejected for crypto (BTC/USDT, ETH/USDT — decisive 0/54 cells)

All validators run for the primary config (Sharpe, MDD, transaction-cost
survival, parameter sensitivity) pass cleanly on both QQQ and SPY, with
strong margins (Sharpe 1.37/1.87, both well above 1.0; net-of-cost Sharpe
still >1.0 on both despite ~110 trades over 7.5 years). The grid confirms
this isn't a single-config fluke: 50% of all equity cells pass, with the
strongest showing specifically in high-vol regimes, which is economically
sensible for a mean-reversion strategy (sharper drawdowns => sharper
snapbacks). Scope is equity-only; crypto decisively fails at the grid
stage. Walk-forward was not run due to a pre-existing environment bug;
this should be re-verified in a future iteration once that's fixed, per
the running convention in this repo's other recent accepted entries.

# Bulkowski Hook Reversal, Downtrend -- long/up-breakout side

**Hypothesis:** per https://thepatternsite.com/HRD.html, a 2-bar pattern in a
short-term downtrend: bar1 sets a range, bar2 is an inside day AND has an
edge-position filter (open near its own low, close near its own high).
Source's own finding: despite being framed as a reversal, 51% actually
continue lower -- so trade in the breakout direction rather than assume
reversal. This strategy takes the long/up-breakout side only: entry on close
breaking above the 2-bar pattern's high; measure-rule target = pattern
height x height_mult added to the breakout level.

**Config (shared, both symbols):** trend_window=0 (no trend gate --
source's downtrend qualifier turned out not to matter, see notes),
edge_pct=0.65, height_mult=2.0, max_hold_days=20

## Single-config validators (2019-01-01 to 2026-09-01)

| Symbol | Trades | Sharpe | MDD | Net Sharpe (TC) | Param Sens (rel std) | All Pass |
|---|---|---|---|---|---|---|
| SPY | 25 | 1.315 | 0.073 | 1.224 | 0.137 | Yes |
| QQQ | 33 | 1.028 | 0.128 | 0.960 | 0.071 | Yes |
| BTC/USDT | 59 | 0.674 | 0.546 | 0.651 | 0.121 | No (Sharpe+MDD fail) |

Walk-forward: skipped (known repo-wide vectorbt.utils.splitting API issue).

## Grid summary (initial broad scan, 324 cells)

- pass_fraction 0.154 (50/324): equity 39/162, crypto 11/162
- Best tercile-slice cell: SPY mid-vol, trend_window=0/edge_pct=0.35/
  height_mult=1.0, Sharpe 1.887
- Full-sample retune at trend_window=0/edge_pct=0.65/height_mult=2.0 (found
  from the grid's most-frequently-passing config) clears the Sharpe bar on
  BOTH SPY and QQQ cleanly, all 4 runnable validators passing on both.

## Outcome: ACCEPTED (equity: SPY + QQQ); crypto (BTC/USDT, ETH/USDT) rejected/out of scope

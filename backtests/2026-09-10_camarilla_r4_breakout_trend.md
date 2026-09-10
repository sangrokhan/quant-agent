# Camarilla Pivot R4 Breakout Trend-Continuation (QQQ)

**Hypothesis source:** Google AI-overview synthesis (Medium/Bhaskar Das et al),
via browser_exec Google SERP fallback of "Camarilla pivot points daily trading
strategy R3 R4 S3 S4 rules". Source's own stated rule: "R3/S3 for a
range-bound market [mean reversion]... R4/S4 for breakouts in a trending
market" -- extreme boundary lines whose break "signals a powerful new
directional trend."

**Hypothesis:** Long entry when close breaks above the prior day's Camarilla
R4 level (extreme resistance, camarilla_mult=1.1 default constant); exit
when close falls back below the prior day's pivot (P) or R3 level, or after
a max_hold_days time-stop.

Distinct from this repo's existing Camarilla variant (2026-09-04-119: an
S3/S4-zone mean-reversion fade, the OPPOSITE half of the same indicator
system per the source's own R3/S3-vs-R4/S4 distinction) and from the
classic-pivot S1-bounce (2026-09-07-025, different pivot formula entirely).

Strategy file: `strategies/2026-09-10_camarilla_r4_breakout_trend.py`

## Step 6 grid summary (216 cells: camarilla_mult x exit_level x max_hold_days
x {QQQ,SPY,BTC/USDT,ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 22/216 = 0.102
- `by_asset_class`: equity 22/108 passed; **crypto 0/108 passed** (decisive
  fail)
- `by_vol_regime`: low 0/72; mid 12/72; high 10/72 -- notably this strategy
  works BETTER in mid/high-vol regimes (opposite of most mean-reversion
  strategies in this repo), consistent with it being a breakout/trend
  mechanic
- best cell: camarilla_mult=1.1, exit_level=pivot, max_hold_days=5, QQQ,
  high-vol regime, Sharpe 1.691

## Step 7 single-config validation (QQQ, camarilla_mult=1.1, exit_level=pivot,
max_hold_days=5 -- grid's best cell, full 2019-01-01..2026-09-01 sample)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL (near-miss)** | 0.923 | 1.0 |
| Max drawdown | pass | 0.039 | 0.25 |
| Transaction cost survival (10bps/trade, 58 trades) | pass | 0.560 | 0.5 |
| Walk-forward (4 manual splits) | pass | 1.00 (4/4 splits positive) | 0.75 |
| Parameter sensitivity (18-cell full-sample sweep) | pass | 0.312 relative std | 0.5 |

## Outcome: **rejected (strong near-miss)**

Only the full-sample Sharpe (0.923 vs 1.0 threshold) fails -- every other
validator passes comfortably, including a very low max drawdown (3.9%) and
perfect walk-forward robustness (4/4 splits positive). The grid confirms
this holds up specifically in mid/high-vol regimes (0/72 low-vol), so a
future iteration could try gating entries to mid/high-vol regimes only
(mirroring the earlier BB-meanrev strategy's explicit regime filter, but
inverted) to concentrate the edge and likely push full-sample Sharpe over
1.0. Crypto rejected decisively (0/108 grid cells).

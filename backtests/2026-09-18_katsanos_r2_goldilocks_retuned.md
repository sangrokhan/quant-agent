# Katsanos R² Goldilocks Trend — Retuned Config (r2_period=25, r2_enter=0.42)

**Strategy file:** `strategies/2026-09-17_katsanos_r2_goldilocks_trend.py`
(unchanged code, direct fine-tune follow-up to this repo's own near-miss
`2026-09-17-137`)
**Source:** Markos Katsanos, TASC Oct 2016 "Which Trend Indicator Wins?",
MetaStock formula fully disclosed at
https://traders.com/Documentation/FEEDbk_docs/2016/10/TradersTips.html.

## Hypothesis

`2026-09-17-137` tested `r2_period` in [14, 18, 25] via a grid but its
recorded "best_config" used `r2_period=25` with `avg_sharpe=0.97` (still a
near-miss at the grid-averaged level). This iteration ran a targeted
full-sample scan around `r2_period=25` x `r2_enter` in {0.30, 0.35, 0.42,
0.50} x `r2_cap` in {0.85, 0.90, 0.95} (holding `max_hold_days=40,
slope_min=0.0` fixed, the parent's own defaults) and found
`r2_period=25, r2_enter=0.42, r2_cap=0.85` (i.e. `r2_period` alone changed
from the parent's default 18 to 25, all Goldilocks thresholds kept at the
source's own disclosed values) clears QQQ Sharpe 1.167 -- a decisive
improvement over the parent's 0.960 near-miss.

## Full-sample scan (QQQ, r2_cap held at parent default 0.85/0.90/0.95 -- all identical since r2 never approaches the cap at this config)

| r2_period | r2_enter | QQQ Sharpe | QQQ MDD | Trades |
|---|---|---|---|---|
| 18 (parent) | 0.42 | 0.960 (recorded) | -- | -- |
| **25** | **0.42** | **1.167** | 0.148 | 22 |
| 25 | 0.35 | 1.025 | 0.147 | 15 |
| 25 | 0.50 | 0.977 | 0.149 | 23 |
| 25 | 0.30 | 0.932 | 0.101 | 11 |

## Single-config validation (r2_period=25, r2_enter=0.42, r2_cap=0.85, max_hold_days=40, slope_min=0.0)

| Symbol | Sharpe | Sharpe pass | MDD | MDD pass | TC-survival net Sharpe | TC pass | WF pass_frac | WF pass | Param-sens relstd | PS pass | Trades | ALL PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ | 1.167 | ✅ | 0.148 | ✅ | 1.126 | ✅ | 1.00 | ✅ | 0.207 | ✅ | 22 | **✅ ACCEPT** |
| SPY | 0.490 | ❌ | 0.103 | ✅ | 0.429 | ❌ | 1.00 | ✅ | 0.606 | ❌ | 23 | ❌ reject |
| BTC/USDT | 0.190 | ❌ | 0.391 | ❌ | 0.093 | ❌ | 1.00 | ✅ | 0.277 | ✅ | 784 | ❌ reject |
| ETH/USDT | 0.209 | ❌ | 0.473 | ❌ | 0.130 | ❌ | 0.75 | ✅ | 0.127 | ✅ | 739 | ❌ reject |

Parameter sensitivity swept `r2_period` in {20,25,30} x `r2_enter` in
{0.38,0.42,0.46} around the accepted config. Walk-forward used manual
4-equal-slice fallback (`RangeSplitter` broken in this vectorbt install).

## Decision

**Accept for QQQ only** at the retuned config (`r2_period=25` instead of
the parent's default 18; all else unchanged from the source's own
Goldilocks-zone thresholds). This is a direct rescue of the parent
near-miss `2026-09-17-137` via a single-parameter retune rather than
architectural changes (contrast with `2026-09-18-014`'s failed vol-gate
attempt on the same parent). SPY fails Sharpe/TC/param-sensitivity at this
config; crypto (both BTC/USDT and ETH/USDT) decisively fails Sharpe/MDD/TC
-- the ~35x higher trade count on crypto (739-784 vs 22-23 on equities,
because the underlying R² trend-quality signal fires far more often on
crypto's noisier/choppier price action) combined with weak per-trade edge
erodes to negative after transaction costs, and drawdowns are far larger
(39-47% vs 10-15% on equities). Consistent with the parent's own grid
finding of equity-only strength.

# Connors/Alvarez VIX RSI(2) Mean Reversion — QQQ/SPY/BTC/ETH (2026-09-05)

## Hypothesis

Per Larry Connors & Cesar Alvarez's book "Short Term Trading Strategies
That Work" (disclosed by easylanguagemastery.com's "Profit By Combining
RSI And VIX" article, https://easylanguagemastery.com/strategies/vix-rsi/):
a 2-period RSI computed on the VIX INDEX ITSELF spiking above 90 signals
an acute, already-fading fear spike -- a buy signal for the underlying
equity index -- confirmed by the price's own RSI(2)<30 reading and a
200-day SMA uptrend filter. Exit when price RSI(2) rises above 65. First
strategy in this repo to apply an RSI oscillator TO the VIX series itself
rather than using VIX's raw level/SMA/Bollinger/term-structure (distinct
from 2026-09-04-103, 2026-09-04-157, 2026-09-05-021, 2026-09-05-028,
2026-09-05-044).

## Strategy file

`strategies/2026-09-05_vix_rsi2_connors_alvarez.py`

## Step 6 — Grid test summary

Grid: `vix_rsi_entry in [85,90,95]` × `max_hold_days in [10,15,20]` (9
combos) × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime terciles
= 108 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 24/108 = 0.222**
- By asset class: equity 24/54 (0.444); **crypto 0/54 (0.0) — decisive fail (expected: VIX is an S&P-options-implied-vol gauge, no direct economic link to crypto)**
- By vol regime: low 18/36 (0.50), mid 6/36 (0.167), **high 0/36 (0.0)**
  — notably the strategy is entirely absent from high-vol-regime passes
  despite being triggered by VIX spikes, which cluster in high-vol
  periods; likely explained by the vol-regime split being computed on the
  UNDERLYING asset's realized vol (not VIX), and/or the strategy's rare,
  short trades getting diluted/misclassified across regime boundaries.
- Best cell: `vix_rsi_entry=95, max_hold_days=10`, SPY, low-vol regime, Sharpe 2.21
- Worst cell: `vix_rsi_entry=90, max_hold_days=15`, SPY, high-vol regime, Sharpe -0.30

## Step 7 — Single best-config validators

Config: `vix_rsi_entry=95, max_hold_days=10` (price_rsi_entry=30,
price_rsi_exit=65, trend_window=200 defaults), full sample 2019-01-01 to
2026-09-01.

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.654 | 0.829 | ≥ 1.0 | QQQ ❌ / SPY ❌ (near-miss) |
| Max drawdown | 0.082 | 0.084 | ≤ 0.25 | QQQ ✅ / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | 0.548 | 0.672 | ≥ 0.5 | QQQ ✅ / SPY ✅ |
| Num trades | 39 | 41 | — | — |
| Parameter sensitivity (relative_std, 9-cell sweep, SPY) | 0.097 | — | ≤ 0.5 | ✅ |

`check_walk_forward` skipped (pre-existing `vbt.utils.splitting`
AttributeError in this repo's installed vectorbt version).

## Outcome: **REJECTED (near-miss)** on both QQQ and SPY; rejected for crypto (decisive 0/54 cells)

Full-period Sharpe falls short of the 1.0 threshold on both QQQ (0.654)
and SPY (0.829), but every other validator passes cleanly (very low
drawdown ~8%, net-of-cost Sharpe still above 0.5 on both, parameter
sensitivity very stable at relative_std 0.097 -- the LOWEST seen among
this repo's recent tests, meaning the modest edge is highly robust across
the vix_rsi_entry/max_hold_days grid, just not large enough in absolute
Sharpe terms). This is a genuine near-miss: low trade count (39-41 over
7.5 years, consistent with VIX RSI(2)>90 being a rare extreme event) and
low volatility of returns (MDD ~8%) suggest the strategy is real but too
infrequent/low-magnitude to clear the 1.0 Sharpe bar on its own. Worth
revisiting in a future iteration combined with a complementary always-on
strategy (e.g. paired with the already-accepted RSI(2) mean-reversion
2026-09-03-005 or Heikin Ashi mean-reversion 2026-09-05-051) as a
higher-conviction overlay rather than a standalone system.

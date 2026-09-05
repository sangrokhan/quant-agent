# Ichimoku Kumo Breakout — QQQ/SPY/BTC/ETH (2026-09-05)

## Hypothesis

Price breaking above the Ichimoku Kumo cloud (max of Senkou Span A / B)
signals a confirmed uptrend worth being long in; breaking below signals
exit/breakdown. Source: TrendSpider, "Ichimoku Cloud Trading Strategies"
(https://trendspider.com/learning-center/ichimoku-cloud-trading-strategies/),
the "Kumo Breakout" rule. Distinct from the previously-tested Tenkan/Kijun
cross + cloud-confirmation Ichimoku variant (2026-09-04-034, near-miss
rejected) — this strategy's ONLY trigger is the price/cloud-boundary
crossover itself.

## Strategy file

`strategies/2026-09-05_ichimoku_kumo_breakout.py`

Params: `tenkan_window` (default 9), `kijun_window` (26), `senkou_b_window`
(52), `displacement` (26), `max_hold_days` (40).

## Step 6 — Grid test summary

Grid: `tenkan_window in [7,9,12]`, `kijun_window in [22,26,30]`,
`max_hold_days in [30,40]` (18 combos) × symbols `{QQQ, SPY, BTC/USDT,
ETH/USDT}` × 3 vol-regime terciles = 216 cells, 2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 44/216 = 0.204**
- By asset class: equity 44/108 (0.407) passed; **crypto 0/108 (0.0) — decisive fail**
- By vol regime: low 36/72 (0.50), mid 5/72 (0.07), high 3/72 (0.04)
- Best cell: `tenkan_window=7, kijun_window=22, max_hold_days=40`, QQQ, low-vol regime, Sharpe 2.13
- Worst cell: `tenkan_window=12, kijun_window=22, max_hold_days=40`, QQQ, high-vol regime, Sharpe -0.84

Interpretation: the Kumo breakout only earns its edge in low-realized-vol
equity slices; it fails decisively in mid/high-vol equity regimes and
across all of crypto.

## Step 7 — Single best-config validators

Config: `tenkan_window=7, kijun_window=22, max_hold_days=40`, full sample
2019-01-01 to 2026-09-01 (not vol-regime-sliced).

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe ratio | 0.600 | 0.435 | ≥ 1.0 | QQQ ❌ / SPY ❌ |
| Max drawdown | 0.258 | 0.233 | ≤ 0.25 | QQQ ❌ / SPY ✅ |
| Net Sharpe after costs (10bps/trade) | 0.555 | 0.378 | ≥ 0.5 | QQQ ✅ / SPY ❌ |
| Num trades | 29 | 32 | — | — |
| Parameter sensitivity (relative_std, 9-cell tenkan×kijun sweep, QQQ) | 0.189 | — | ≤ 0.5 | ✅ |

`check_walk_forward` was **not run** — `vbt.utils.splitting.RangeSplitter`
raises `AttributeError: module 'vectorbt.utils' has no attribute
'splitting'` in this repo's installed vectorbt version (a pre-existing
environment issue, consistent with other recent log entries).

## Outcome: **REJECTED** (all symbols/asset classes)

Full-period Sharpe fails decisively on both QQQ and SPY (well below the
1.0 threshold, despite the grid's low-vol-regime cells looking strong —
Sharpe 2.13 on QQQ-low-vol). MDD additionally fails on QQQ (0.258 > 0.25)
and net-of-cost Sharpe fails on SPY (0.378 < 0.5). Crypto rejected
decisively at the grid stage (0/108 cells). Parameter sensitivity itself
is fine (relative_std 0.19), so this is not a fragile-parameter issue —
the edge is real but genuinely narrow (low-vol equity only) and does not
survive full-period unconditional testing. Consistent with the broader
pattern in this repo (see 2026-09-04-034 near-miss) that raw Ichimoku
cloud signals need an explicit volatility-regime gate to be viable; a
future iteration could revisit this exact rule WITH a low-vol regime
filter analogous to 2026-09-03-001 (BB mean-reversion + vol regime gate)
rather than trading the Kumo breakout unconditionally.

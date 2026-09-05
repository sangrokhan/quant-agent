# Wednesday Turnaround (Weak-Tuesday Mean Reversion) — Backtest Report

**Hypothesis:** QuantifiedStrategies.com's "Wednesday Turnaround Strategy"
is explicitly described as "a cousin of the Tuesday Turnaround Strategy"
(disclosed SPY backtest stats: 330 trades, 0.7% avg gain/trade, 63% win
ratio, profit factor 2.1, CAGR 6.6%, exposure 19%, MDD 21% -- exact rule
paywalled). The companion Turnaround Tuesday article's own disclosed
mechanism (Google search snippet): "buying on a weak Monday, where the
close is at least 1% lower than Friday's close, and selling at Tuesday's
close." Operationalized here shifted one weekday: buy on a weak Tuesday
(close >= 1% below Monday's close), sell at Wednesday's close.

**Source:** https://www.quantifiedstrategies.com/wednesday-turnaround-strategy/
(disclosed stats) + Google SERP snippet of the Turnaround Tuesday Strategy
article (disclosed weak-close mechanism, "cousin" relationship implies the
same mechanism shifted one weekday).

**Strategy file:** `strategies/2026-09-05_wednesday_turnaround_weak_tuesday.py`

## Step 6 — Grid test summary (param_grid: weak_pct in [0.005, 0.01, 0.015];
symbols: equity QQQ/SPY, crypto BTC/USDT, ETH/USDT; vol_regime_splits=3;
period 2019-01-01..2026-09-01)

- total_cells: 36, passed_cells: 6, **pass_fraction: 0.167**
- by_asset_class: equity 6/18 (33%), crypto 0/18 (0%, decisive fail --
  consistent with the already-rejected day-of-week strategies in this
  repo, no comparable weekly institutional cash-flow cycle for crypto)
- by_vol_regime: low 0/12 (0%), mid 1/12 (8%), high 5/12 (42%)
- best_cell: weak_pct=0.015, QQQ, high-vol, Sharpe=1.574
- worst_cell: weak_pct=0.015, SPY, mid-vol, Sharpe=-0.728

## Step 7 — Single-config validators (config: weak_pct=0.01, full
unconditional 2019-2026 sample)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>= 1.0) | FAIL 0.817 | FAIL 0.477 |
| Max Drawdown (<= 0.25) | PASS 0.097 | PASS 0.053 |
| Transaction cost survival (net Sharpe >= 0.5, 10bps/trade) | PASS 0.597 (72 trades) | FAIL 0.321 (45 trades) |
| Parameter sensitivity (relative_std <= 0.5, weak_pct {0.005,0.01,0.015} sweep) | PASS 0.063 | PASS 0.176 |

Walk-forward not run: `check_walk_forward` hits the pre-existing
`vbt.utils.splitting` AttributeError bug in this repo's installed vectorbt
version (same known issue as other recent entries).

## Outcome: **REJECTED**

Sharpe fails decisively on both QQQ (0.817, near-miss) and SPY (0.477) over
the full unconditional sample; SPY additionally fails transaction-cost
survival. Like the two prior day-of-week strategies tested in this repo
(2026-09-03-018 plain Turnaround Tuesday, 2026-09-04-105 volume-gated
variant), this weak-close-magnitude-gated Tuesday->Wednesday variant does
not clear the 1.0 Sharpe bar unconditionally, though the grid shows a
genuine (if narrow) edge concentrated in the equity high-vol tercile
(consistent with a "panic overreaction, next-day mean-reversion" mechanism
that should logically need volatility to manifest). Crypto fails
completely (0/18), reinforcing that this repo's day-of-week family of
signals has no crypto analog. Not revisited further this iteration.

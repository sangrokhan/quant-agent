# 2026-09-11 Plain ROC Zero-Line Crossover + 200d Trend Gate (QQQ/SPY) — ACCEPTED

**Hypothesis:** Per QuantifiedStrategies.com's "Price Rate of Change
Strategy (ROC Indicator – Trading Rules and Backtest, Performance)"
(https://www.quantifiedstrategies.com/rate-of-change-trading-strategy/,
visited 2026-09-11), source's own disclosed rule: "Buy when ROC crosses
from negative to positive... Sell or short when ROC crosses from positive
to negative," plus source's own caveat that this needs "filters or
additional rules (e.g., trend confirmation) to avoid whipsaws" in
sideways markets. This is the first plain single-period ROC zero-cross
test in the repo (prior ROC-family entries -- Coppock Curve, KST -- are
all multi-leg weighted composites). Long-only adaptation: enter when
ROC(roc_window) crosses from <=0 to >0 AND close > SMA(trend_window)
(source's own suggested trend filter); exit on ROC crossing back below 0,
trend filter breaking, or a max_hold_days time-stop.

## Grid test (roc_window in [10,12,20] x trend_window in [100,200] x max_hold_days in [20,30], QQQ/SPY/BTC-ETH, 3 vol terciles, 2018-01-01..2026-09-01)

- total_cells: 144, passed_cells: 37, **pass_fraction: 0.257** (repo-best so far this cron trigger)
- by_asset_class: equity 37/72 passed, crypto 0/72 passed (decisive rejection on crypto)
- by_vol_regime: low 24/48, mid 11/48, high 2/48 (edge concentrated in low/mid-vol, some presence in high-vol too, broader than prior 2 rejected iterations this trigger)
- best_cell: roc_window=12, trend_window=200, max_hold_days=30, QQQ, low-vol, Sharpe=3.02
- Averaging Sharpe across all equity symbols/regimes per param combo, roc_window=12/trend_window=200/max_hold_days=30 is the clear best (avg Sharpe 1.35 across 6 equity cells)

## Single-config validation (roc_window=12, trend_window=200, max_hold_days=30 -- grid's best avg config, full sample)

| Metric | QQQ | SPY | Threshold | Pass? |
|---|---|---|---|---|
| Sharpe (full sample) | 1.208 | 1.379 | >= 1.0 | **PASS both** |
| Max Drawdown | 0.133 | 0.095 | <= 0.25 | **PASS both** |
| TC survival (10bps/trade, 86-89 trades/8yr) | 1.040 | 1.121 | >= 0.5 | PASS |
| Walk-forward (4 splits) | 1.0 | 1.0 | >= 0.75 | PASS |
| Parameter sensitivity (12-cell grid rel-std) | 0.227 | 0.170 | <= 0.5 | PASS |

## Decision: ACCEPTED (equity only: QQQ, SPY)

All 5 validators pass cleanly for both QQQ and SPY at the grid-optimal
config (roc_window=12, trend_window=200, max_hold_days=30). Sharpe ratios
(1.21 QQQ, 1.38 SPY) comfortably clear the 1.0 threshold, max drawdowns
are low (9.5-13.3%), transaction costs are well survived even after
10bps/trade friction on ~86-89 trades over 8 years, walk-forward is
perfect (4/4 splits positive Sharpe), and parameter sensitivity is low
(rel-std 0.17-0.23, well under the 0.5 threshold) -- the strategy is not
fragile to the exact parameter choice. Crypto (BTC/USDT, ETH/USDT) is
decisively rejected (0/72 grid cells) and should NOT be traded with this
strategy -- scope explicitly limited to equity index ETFs (QQQ/SPY). Edge
is strongest in low/mid-vol regimes but shows some presence in high-vol
too (2/48), broader vol-regime robustness than the two rejected
strategies earlier this cron trigger.

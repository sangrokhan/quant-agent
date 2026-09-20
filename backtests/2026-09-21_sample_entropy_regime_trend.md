# Sample Entropy Regime Trend Strategy — Backtest Report (2026-09-21)

## Hypothesis

Per GospodarValovaHR's "Sample Entropy (SampEn) Regime Detector" TradingView
indicator (https://www.tradingview.com/script/1ZBMuq8g-Sample-Entropy-SampEn-Regime-Detector/,
read via `browser_exec` after `web_search`'s DDGS backend TLS-erroring on the
detail-formula follow-up query): Sample Entropy quantifies how
predictable/regular vs. chaotic/random recent price action is over a
rolling window. Low SampEn = structured (trend/mean-reversion) regime where
standard strategies work; high SampEn (>~2.0 per the source's own
suggestion) = noisy/chop regime to avoid.

This strategy gates a plain SMA(fast) > SMA(slow) trend crossover long
entry by requiring rolling classic Richman & Moorman (2000) Sample Entropy
of log returns to be below `sampen_threshold`. First Sample-Entropy-based
strategy in this repo (0 prior "sample entropy"/"sampen" hits) — distinct
from the 1 prior Approximate Entropy entry (SampEn corrects for ApEn's
self-matching bias, a genuinely different algorithm).

## Single-config validators (best config: QQQ, `fast_window=20,
slow_window=100, sampen_threshold=2.0`)

| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | ❌ | 0.481 | ≥ 1.0 |
| Max drawdown | ✅ | 0.224 | ≤ 0.25 |
| Transaction cost survival (10bps/trade, 70 trades) | ❌ | net Sharpe 0.400 | ≥ 0.5 |
| Walk-forward (4 splits, manual fallback) | ✅ | 1.0 pass fraction | ≥ 0.75 |
| Parameter sensitivity (8-combo grid, relative std) | ✅ | 0.149 | ≤ 0.5 |

Full sample: 2018-01-01 to 2026-09-01, daily bars.

## Grid test summary (Step 6)

Grid: `fast_window ∈ {20,30} × slow_window ∈ {50,100} × sampen_threshold ∈
{1.8,2.0}` × symbols `{QQQ, SPY, BTC/USDT, ETH/USDT}` × 3 vol-regime
terciles = 96 cells.

- **Overall pass fraction: 0.28125 (27/96)**
- By asset class: equity 20/48 (0.417), crypto 7/48 (0.146)
- By vol regime: low 17/32 (0.531), mid 10/32 (0.313), high **0/32 (0.0)**
- Best cell: QQQ, low-vol tercile, `fast_window=20, slow_window=100,
  sampen_threshold=2.0` — Sharpe 1.850
- Worst cell: QQQ, high-vol tercile, `fast_window=30, slow_window=50,
  sampen_threshold=1.8` — Sharpe -1.200

**Honest scope**: grid cells decompose cleanly by vol regime (low-vol
strong, high-vol strategy is a decisive 0/32 across every symbol/param
combo), but the best per-regime cell's edge does NOT survive full-sample
Sharpe/TC-cost validation once averaged over the whole 2018-2026 period —
the plain SMA crossover backbone (before even the entropy gate) is not
strong enough on its own, and the low SampEn gate reduces trade count
(70 trades) without lifting Sharpe enough to clear the 1.0 bar or survive
10bps/trade costs.

## Decision

**Reject.** Sharpe ratio (0.481 < 1.0) and transaction-cost-survival
(net Sharpe 0.400 < 0.5) both fail on the full-sample best config. Strategy
file and this report are kept as a record of a rejected attempt — a future
loop revisiting Sample Entropy should note: (a) the regime split shows real
signal (0/32 high-vol pass is a genuinely informative decisive rejection,
not noise), (b) the underlying SMA(20)/SMA(100) crossover entry itself may
be too weak a backbone -- a future iteration could pair the SampEn regime
filter with a stronger base signal (e.g. one of this repo's already-
accepted momentum/breakout entries) instead of a bare crossover.

Sources visited this iteration:
- https://www.tradingview.com/script/1ZBMuq8g-Sample-Entropy-SampEn-Regime-Detector/ (primary source, browser_exec)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC7597144/ (checked -- entropy-based market regime paper, requires news-sentiment data this repo's OHLCV-only loaders can't provide; not pursued)

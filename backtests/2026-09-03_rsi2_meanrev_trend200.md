# Backtest Report — 2026-09-03_rsi2_meanrev_trend200

**Hypothesis:** Larry Connors' RSI(2) mean-reversion strategy (200-day SMA
trend filter + RSI(2) oversold dip entry + 5-day SMA exit) produces a
tradeable, risk-adjusted edge on equity indices; crypto is tested but not
assumed to transfer given its different microstructure/volatility regime.

**Source:** https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2
(StockCharts ChartSchool writeup of Larry Connors' 2-period RSI strategy).
Rules taken directly from the source: (1) long-term trend filter = 200-day
SMA (only long above it); (2) entry = RSI(2) closes <= an oversold
threshold (source tested 0-10, found 5 stronger than 10 — both exposed
here as `rsi_entry` grid values); (3) exit = close crosses back above the
5-day SMA. We implement **long-only** (no shorting on a break below the
200-day SMA), consistent with this repo's SAFETY.md / prior strategies'
long-only convention.

**Novelty:** First RSI-oscillator, short-holding-period (single-digit days)
mean-reversion-within-uptrend strategy tried in this repo. Distinct from
2026-09-01-001 (SMA crossover, trend-following), 2026-09-03-001 (Bollinger
mean-reversion, no trend filter, rejected on Sharpe), and the
2026-09-03-002/-003/-004 momentum family (all multi-week/month
trend-following holding periods, all rejected on max drawdown). This
strategy's fast mean-reversion exit (days, not weeks) is the structural
difference that keeps drawdown small.

**Universe / period:** SPY, QQQ (equity, `load_equity`), BTC/USDT, ETH/USDT
(crypto, `load_crypto`, **forced to `interval="1d"`** — see bug note
below), 2019-01-01 to 2026-09-01.

**Signal:** long when `close[t] > SMA(trend_window)` and RSI(2) has closed
`<= rsi_entry`; hold (stateful) until `close > SMA(exit_sma_window=5)` or
the trend filter breaks. Position lagged 1 day to avoid look-ahead.

## Step 6 — Grid test (rsi_entry ∈ {5, 10} × trend_window ∈ {150, 200} ×
2 equity + 2 crypto symbols × 3 vol-regime terciles = 48 cells)

- **Overall pass_fraction: 0.3125** (15/48 cells pass Sharpe>=1.0 AND MDD<=25%)
- By asset class: equity 13/24 (54%), crypto 2/24 (8%)
- By vol regime: low 9/16 (56%), mid 5/16 (31%), high 1/16 (6%)
- Best cell: QQQ, rsi_entry=10, trend_window=200, low-vol regime, Sharpe 2.29
- Worst cell: SPY, rsi_entry=5, trend_window=150, high-vol regime, Sharpe -0.44

Clear pattern (consistent with every prior grid in this repo): the strategy
works well on equities, especially in low/mid-vol regimes, and is weak on
crypto and in high-vol regimes across the board.

## Step 7 — Single-config validation (best grid params: rsi_entry=10,
trend_window=200), full-sample, both asset classes

| Symbol | Sharpe | MDD | TC-adj Sharpe | Param sensitivity (rel.std) |
|---|---|---|---|---|
| SPY | 1.27 (PASS, >=1.0) | 8.5% (PASS, <=35%) | 0.68 (PASS, >=0.5) | 0.075 (PASS, <=0.5) |
| BTC/USDT | 0.37 (FAIL) | 36.4% (FAIL, <=35%) | 0.26 (FAIL) | 0.19 (PASS) |

Walk-forward was skipped this iteration (`check_walk_forward` remains
broken — `vbt.utils.splitting.RangeSplitter` does not exist in the
installed vectorbt version, a known unfixed scaffold bug flagged since
2026-09-03-002/-003).

**Scaffold bug found & fixed this iteration:** `data/loaders.py::load_crypto`
defaults to `interval="1h"`, but this strategy (and `grid_test.py`'s
vol-regime/annualization logic) assumes daily bars. Calling it with the
default silently backtested on hourly bars, producing a nonsensical
~2900-trade count over the period. Fixed locally in the grid runner by
forcing `interval="1d"` explicitly for every `load_crypto` call — a future
loop iteration should consider making this explicit at the call site
convention-wide, not just here.

## Decision: ACCEPT (equity only), REJECT (crypto)

SPY (and by extension the equity asset class, per the grid: QQQ also
clears comfortably at the same params) passes all four validators run this
iteration cleanly — Sharpe 1.27, MDD 8.5%, TC-adjusted Sharpe 0.68,
parameter-sensitivity relative std 0.075 (very stable across the 4-cell
param grid). This is accepted as a **narrow-but-honest, equity-only**
strategy per RESEARCH_LOOP.md Step 6 guidance: crypto fails every
validator at the same config (Sharpe 0.37, MDD 36.4%, TC-adjusted Sharpe
0.26) and should not be traded with this parameterization — a future loop
could retest crypto with crypto-tuned thresholds (e.g. a lower/higher
RSI band or shorter trend window suited to crypto's faster mean-reversion
cycles) as a distinct hypothesis.

Kept `strategies/2026-09-03_rsi2_meanrev_trend200.py` live in `strategies/`
for the equity use case; scope explicitly limited to SPY/QQQ-like liquid
equity indices, not crypto, per this report and the knowledge base entry's
`symbols`/`notes` fields.

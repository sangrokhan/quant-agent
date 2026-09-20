# Backtest Report: Stock-to-Flow (S2F) Deviation Hysteresis Gate (BTC)

**Strategy file:** `strategies/2026-09-20_s2f_deviation_hysteresis.py`
**Date:** 2026-09-20
**Hypothesis:** PlanB's Stock-to-Flow model (S2F = circulating supply /
annual issuance), published log-linear fit `ln(market value) = 3.3*ln(S2F)
+ 14.6` (equivalently `model_price ~= 0.18 * S2F^3.3`, per Bitcoin.com
Charts' restated per-coin form, corroborated by TradingView's "Stocktoflow"
script `ln(Model Price) = 3.3297*ln(S2F) - 12.214`). A ResearchGate-indexed
paper ("Dissecting the stock to flow model for Bitcoin") describes a
dynamic long/short-on-deviation trading strategy. Tested here as a
long/flat hysteresis: long while price <= model_price*(1-band), flat once
price >= model_price*(1+band).

Sources: https://www.lookintobitcoin.com/charts/stock-to-flow-model/ ,
Medium/PlanB "Modeling Bitcoin Value with Scarcity" (via Google SERP
snippet), https://charts.bitcoin.com (formula restatement), TradingView
"Stocktoflow" indicator page (all via Google SERP + browser_exec since
web_search DDGS returned no usable results for this query chain).

## Model sanity check

Computed the deterministic S2F model price (from public halving schedule +
BTC/USDT close) over the 2019-2026 backtest sample:
- Model price is **always far above** actual BTC/USDT close in this sample
  (e.g. 2026-09-01: model ~$1.39M vs actual close ~$77.4K, ratio ~0.056;
  even at the 2021 bull peak the ratio only reached ~0.37) -- a well-known
  real-world divergence of the S2F model from actual price since ~2021,
  now baked into this repo's backtest window.
- Consequence: at any economically sane `band` (0.1-0.5), price never
  crosses the exit line (`model_price*(1+band)`), so the strategy stays
  **permanently long** (position mean = 1.0 at band=0.5) -- i.e. the signal
  degenerates to buy-and-hold, not a genuine deviation-timing signal, for
  most of this bull-heavy sample window.

## Grid test summary (Step 6)

`band in [0.1, 0.2, 0.3, 0.5]`, symbols `{equity: [QQQ, SPY], crypto:
[BTC/USDT, ETH/USDT]}`, vol_regime_splits=3, 2019-01-01 to 2026-09-01.

- total_cells: 48, passed_cells: 12, pass_fraction: 0.25
- by_asset_class: equity 12/24 passed, **crypto 0/24 passed**
- by_vol_regime: low 8/16, mid 4/16, **high 0/16**
- best_cell: equity/QQQ/low-vol, band=0.1, Sharpe 2.58
- worst_cell: crypto/ETH-USDT/high-vol, band=0.1, Sharpe 0.42

As with the equity "passes" on this iteration's earlier Puell Multiple
attempt, the equity cells are not evidence for the hypothesis -- S2F is
BTC-specific by construction and is economically meaningless applied to
QQQ/SPY price. The actual target asset (crypto, especially BTC) has a
**0% grid pass rate**.

## Single-config validators (Step 7)

Full-sample BTC/USDT (2019-01-01 to 2026-09-01), band=0.5 (near-permanent
long, closest to a buy-and-hold baseline for this asset over this window):
Sharpe 0.951 (< 1.0 threshold, **fail**), MDD 0.766 (>> 0.25 threshold,
**fail**).

## Decision: REJECT

- Crypto (the hypothesis's actual target asset): 0/24 grid pass across all
  4 band values and all 3 vol regimes, including 0/16 in the high-vol
  tercile specifically.
- The model's own real-world 2021+ divergence from actual BTC price makes
  any deviation-band construction degenerate to buy-and-hold in this
  sample, which itself fails the Sharpe/MDD thresholds on BTC/USDT over
  2019-2026 (large drawdowns during 2022 bear market and 2026 correction).
- Equity cells (out-of-scope sanity check, not evidence for the hypothesis)
  pass only because QQQ/SPY have strong secular uptrends independent of any
  BTC-specific supply-schedule signal -- not a genuine test.

Architecturally distinct from this repo's "on-chain data infeasible" dead
ends (MVRV/NUPL/SOPR): the S2F stock/flow inputs are fully derivable from
the public halving schedule alone (same feasibility argument as this
trigger's earlier Puell Multiple strategy, 2026-09-20-097), so this is a
genuine negative result, not another feasibility block.

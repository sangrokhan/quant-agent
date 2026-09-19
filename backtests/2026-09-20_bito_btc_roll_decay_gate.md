# BITO/BTC "Futures-Roll-Decay Rate" Gate — REJECTED

**Hypothesis source:** Yahoo Finance, TrendSpider, Binance Academy, Seeking
Alpha, CoinDesk (Google SERP snippets, read via browser_exec; the initial
web_search returned normal results for this query so no fallback was
needed) on BITO (ProShares Bitcoin Strategy futures ETF) structurally
underperforming spot BTC via expense ratio + contango roll-cost bleed.

## Hypothesis

BITO's persistent decay relative to spot BTC is proportional to current
futures-market contango severity. Since this repo's OHLCV-only loaders
can't observe the CME futures curve directly, used the BITO/BTC price
ratio's rolling rate-of-change as an observable proxy: an accelerating
decline (ROC in its own bottom decile) flags a steepening-contango /
crowded-long-futures regime, hypothesized to precede spot deleveraging
risk. Gate: flat on SMA trend-following whenever the ROC decile-flags;
long otherwise.

## Step 6 — Grid summary (144 cells: 3 trend_sma_window x 2 roc_window x 2
decile_threshold x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles,
2021-10-20..2026-09-01 -- sample constrained to BITO's launch date)

- `pass_fraction`: 0.326 (47/144)
- `by_asset_class`: equity 28/72 (38.9%), crypto 19/72 (26.4%)
- `by_vol_regime`: low 28/48 (58.3%), mid 14/48 (29.2%), high 5/48 (10.4%)
- Best cell: QQQ, `trend_sma_window=100, roc_window=20, decile_threshold=0.1`,
  low-vol tercile, Sharpe 2.18.

## Step 7 — Full-sample validators

**BTC/USDT** at `trend_sma_window=100, roc_window=20, decile_threshold=0.2`:

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.207 | >= 1.0 | PASS |
| Max drawdown | 0.209 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 222 trades) | 0.952 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 0.50 (2/4 splits positive) | >= 0.75 | **FAIL** |
| Parameter sensitivity | 0.179 | <= 0.5 | PASS |

**QQQ** at `trend_sma_window=150, roc_window=20, decile_threshold=0.2`:

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.063 | >= 1.0 | PASS |
| Max drawdown | 0.109 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 194 trades) | 0.563 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 0.50 (2/4 splits positive) | >= 0.75 | **FAIL** |

## Step 8 — Decision

**REJECT** both candidate configs. Sharpe/MDD/TC-survival/param-sensitivity
all pass comfortably, but walk-forward fails decisively for BOTH BTC/USDT
and QQQ (only 2/4 splits positive each) — the short ~5-year BITO-constrained
sample (vs. 7+ years for other strategies in this repo) makes a 4-way
walk-forward split brittle/noisy, and the failure pattern (different splits
failing for each symbol) suggests genuine regime-dependence rather than a
uniform look-back artifact. Strategy/backtest files kept as a rejected
record per Step 8 guidance.

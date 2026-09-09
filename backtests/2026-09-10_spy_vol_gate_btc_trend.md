# Backtest report: SPY realized-volatility regime gate on BTC trend-following

**Strategy file:** `strategies/2026-09-10_spy_vol_gate_btc_trend.py`
**Hypothesis id:** see `knowledge_base/strategies_log.jsonl` entry
2026-09-10-034

## Source

Conrad, Custovic & Ghysels (2018), "Long- and Short-Term Cryptocurrency
Volatility Components: A GARCH-MIDAS Analysis", *Journal of Risk and
Financial Management* (MDPI), https://www.mdpi.com/1911-8074/11/2/23
(440+ citations). Headline finding (via Google AI-overview summary of the
abstract/conclusions): S&P 500 realized volatility has a NEGATIVE and
highly significant effect on Bitcoin's LONG-TERM volatility component —
elevated equity RV precedes structurally lower subsequent Bitcoin
volatility.

## Hypothesis

BTC/USDT SMA(trend_window) trend-following long, gated to only participate
when SPY's own trailing realized volatility is ABOVE `spy_vol_threshold`
(the regime the paper associates with subsequently calmer/lower Bitcoin
volatility, hypothesized here as more tradeable for trend-following).

## Grid test (Step 6)

`param_grid={"spy_vol_threshold": [0.12, 0.18], "trend_window": [50, 100]}`
× `symbols={"equity": ["SPY","QQQ"], "crypto": ["BTC/USDT","ETH/USDT"]}` ×
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01, `spy_vol_window=20` fixed.

- **crypto (the actual hypothesis under test): 0/24 cells passed.**
  Sharpe values ranged from -0.06 to 0.36 across all combinations of
  symbol (BTC/USDT, ETH/USDT), vol regime, and parameter — no cell came
  close to the 1.0 threshold.
- Equity cells (SPY/QQQ, gated by SPY's OWN vol on itself, or QQQ gated by
  SPY vol) showed some cells passing (e.g. QQQ mid-vol Sharpe up to 2.03),
  but this is a confound, not a validation of the hypothesis under test —
  SPY-gated-by-SPY-vol is a near-tautological construction, and the
  research question was specifically about equity-vol spilling into
  CRYPTO. These equity results are recorded for completeness but do not
  rescue the hypothesis.

## Single-config validator (BTC/USDT, trend_window=50, spy_vol_threshold=0.12, full period)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | 0.192 | ≥ 1.0 | **FAIL** |
| Max drawdown | 0.545 | ≤ 0.25 | **FAIL** |

## Decision

**Rejected — decisively.** The core hypothesis (SPY realized-vol regime
gates BTC trend-following) fails on crypto across the entire 24-cell grid
(0/24 pass, weak Sharpes throughout) and fails both single-config
validators badly (Sharpe 0.19, MDD 54.5%). The Conrad et al. finding
about equity-vol→Bitcoin-vol spillover, even if statistically real in
their GARCH-MIDAS framework, does not translate into a usable trading
signal via this simple regime-gate construction — most likely because the
"long-term volatility component" in their model is a smoothed/MIDAS-
weighted quantity operating on a much longer horizon than a raw 20-day
realized-vol threshold can approximate. No further validators run given
the decisive grid failure.

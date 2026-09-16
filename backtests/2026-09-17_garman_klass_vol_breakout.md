# Garman-Klass Volatility Percentile Compression Breakout — Backtest Report

**Date:** 2026-09-17
**Strategy file:** `strategies/2026-09-17_garman_klass_vol_breakout.py`
**Source:** https://pinescriptforge.com/strategy/garman-klass-volatility (visited this iteration via browser_exec fallback after web_search returned no results for this query)

## Hypothesis

Garman-Klass volatility uses all four OHLC prices to estimate realized
volatility more efficiently than close-to-close methods, which should let
it flag volatility-regime transitions (compression -> expansion) earlier.
Source's disclosed rule: "Enter breakout when GK volatility begins
expanding from a low percentile. Direction based on the first 1x ATR
breakout from the compression range. Exit when GK volatility peaks and
begins contracting. Trail at 1.5x ATR." Implemented long-only per repo
convention with a percentile-rank compression gate, 1x-ATR breakout entry,
and a combined GK-decline/ATR-trailing-stop/time-stop exit.

## Grid test summary (Step 6)

`param_grid={"compression_pctile": [0.15, 0.20, 0.25], "atr_mult_stop": [1.5, 2.0]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 72 total cells.

- **Overall pass_fraction: 0.306** (22/72 cells pass min_sharpe=1.0/max_mdd=0.25)
- **By asset class:** equity 0/36 passed; crypto 22/36 passed
- **By vol regime:** low 10/24 passed; mid 12/24 passed; **high 0/24 passed**
- **Best cell:** BTC/USDT, compression_pctile=0.25/atr_mult_stop=1.5, low-vol tercile, Sharpe 1.56
- **Worst cell:** QQQ, compression_pctile=0.20/atr_mult_stop=1.5, high-vol tercile, Sharpe -1.01

Equity (QQQ/SPY) fails decisively across all cells and vol regimes — the
compression-breakout logic does not transfer to lower-volatility, more
mean-reverting equity index ETFs. Crypto shows real edge, but exclusively
in low/mid volatility terciles; the high-vol tercile is a clean, consistent
loser across every crypto param combo tested (consistent with a breakout
strategy getting whipsawed during volatility spikes rather than catching
trend continuation).

## Single-config validation (best crypto config: BTC/USDT, compression_pctile=0.25, atr_mult_stop=2.0)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio (full sample) | **FAIL** | 0.268 | >= 1.0 |
| Max drawdown | PASS | 0.167 | <= 0.25 |
| Transaction cost survival (10bps/trade, 307 trades) | **FAIL** | net Sharpe 0.163 | >= 0.5 |
| Walk-forward (4 splits) | PASS | 1.0 pass fraction | >= 0.75 |
| Parameter sensitivity (9-combo sweep) | PASS | relative std 0.067 | <= 0.5 |

The full-sample Sharpe (0.268) is far below the grid's low-vol-tercile
Sharpe (~1.56) because the full sample includes the consistently-losing
high-vol tercile, which drags the blended full-period Sharpe down —
confirming the grid's regime finding rather than contradicting it. The
strategy also generates too many trades (307 over the sample) for its edge
to survive realistic transaction costs.

## Decision: **REJECTED**

2 of 5 validators fail (Sharpe, transaction-cost survival) on the
full-sample/best-available config. The strategy shows a real, walk-forward-
robust, parameter-stable edge on crypto specifically confined to low/mid
realized-volatility regimes, but that edge does not survive blending across
the full volatility cycle nor realistic trading costs, and it does not
transfer to equity at all. Not accepted as a live strategy; file kept in
`strategies/` as a record of a rejected attempt with a well-characterized,
regime-narrow finding for a future loop to potentially revisit with an
explicit volatility-regime gate added on top (a fix worth trying: add a
GK-vol-based regime filter that keeps the strategy flat during the top
realized-vol tercile, rather than trading through it).

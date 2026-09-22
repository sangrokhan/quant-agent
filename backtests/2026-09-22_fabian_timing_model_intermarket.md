# Fabian Timing Model — Intermarket 39-Week SMA Regime Filter (QQQ/SPY)

**Date:** 2026-09-22
**Source:** https://www.quantifiedstrategies.com/fabian-timing-model/ (Richard Fabian, 1960s, "The Mutual Fund Wealth Builder")
**Strategy file:** `strategies/2026-09-22_fabian_timing_model_intermarket.py`

## Hypothesis
A weekly trend-following regime filter that requires three broad-market
indices (S&P 500, Dow Jones Industrial Average, Utilities sector) to agree
reduces false signals versus a single-index trend filter: buy/hold when all
three are above their own 39-week SMA; go flat when 2+ drop below. We proxy
the three indices with SPY, DIA, XLU ETFs. Signal is computed weekly and
forward-filled to daily granularity for whatever asset is being traded.

## Grid test summary (ma_weeks in {26, 39, 52}, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles)

- **36 total cells, 6 passed (pass_fraction = 0.167)**
- By asset class: equity 6/18 passed, **crypto 0/18 passed** (crypto has no
  weekly Friday-close regime structure matching a US-market-hours intermarket
  signal, and DIA/XLU don't map onto 24/7 crypto trading)
- By vol regime: all 6 passes concentrated in the **low-vol tercile** (0/12
  mid, 0/12 high)
- Best cell: `ma_weeks=39`, SPY, low-vol, Sharpe 2.47 (source's own disclosed
  parameter value is also the best-performing one in our independent grid)
- Worst cell: `ma_weeks=52`, ETH/USDT, low-vol, Sharpe -0.49

## Single-config validators (ma_weeks=39, the source's own value)

| Validator | SPY | QQQ |
|---|---|---|
| Sharpe ratio (>=1.0) | 0.758 — **FAIL** | 0.854 — **FAIL** |
| Max drawdown (<=25%) | 20.7% — pass | 21.9% — pass |
| Transaction cost survival (net Sharpe >=0.5 @ 10bps) | 0.731 — pass | 0.835 — pass |
| Walk-forward (4-split, >=75% positive-Sharpe splits) | 75% — pass | 100% — pass |
| Parameter sensitivity (relative std <=0.5) | 0.203 — pass | 0.203 — pass |

## Decision: REJECTED (near-miss)

Full-sample Sharpe fails the >=1.0 threshold on both QQQ and SPY (0.76/0.85),
despite passing all 4 other validators. This is directly consistent with the
source article's own conclusion: "the model's real value is not necessarily
that it is 'perfect'... its strongest appeal is risk reduction, not
necessarily superior long-term returns" — max drawdown is dramatically
better than a naive full-exposure baseline, but risk-adjusted return alone
doesn't clear our Sharpe bar. Grid test also confirms it only earns its keep
in low-vol regimes and is entirely infeasible on crypto (0/18 cells).

Kept as a record of a rejected near-miss (all-but-Sharpe passing); not
promoted to a "live" strategy.

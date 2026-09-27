# Backtest Report: Flush Reversion Tail-Decline

**Strategy file:** `strategies/2026-09-27_flush_reversion_tail_decline.py`
**Date:** 2026-09-27
**Source:** Dashyan, A. (2026), "The Tail Is the Only Signal: Flush Reversion
in Equity Indices and Crypto Perpetual Futures" (SSRN Working Paper,
abstract=7363482, https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7363482
-- read via browser_exec this iteration; web_search DDGS backend returned
empty results on the direct query, corroborated via Google SERP + AI
overview summary of the same paper).

## Hypothesis

After correcting for date-clustering, nested-threshold leakage, multiple
testing, and anti-conservative bootstrap block length, the paper finds
exactly ONE statistically robust equity-index result across 76 years of US
index history: single-day declines <= -7% are followed by a mean
next-session return of +3.08% (familywise p=0.006), while crypto perpetuals
show the SAME mechanism failing completely (edge net of market beta negative
in every regime/year of a 6-year sample). This strategy implements the
disclosed rule as a testable single-asset long/flat signal on both asset
classes specifically to confirm/document that documented asymmetry in this
repo's own grid.

## Single-config metrics (QQQ, decline_threshold=0.07, hold_days=1)

| Validator | Value | Threshold | Passed |
|---|---|---|---|
| Sharpe ratio | -0.429 | >= 1.0 | **FAIL** |
| Max drawdown | 0.147 | <= 0.25 | pass |
| Transaction cost survival | not run (decisive Sharpe fail already) | - | skipped |
| Walk-forward | not run (decisive Sharpe fail already) | - | skipped |
| Parameter sensitivity | see grid below | - | see grid |

Only 2 trading days out of ~2,900 (2015-01-01 to 2026-09-01) triggered a
qualifying >=7% single-day decline on QQQ in this sample — an extremely
sparse signal, consistent with the paper's own finding that only 50 events
on 25 dates survived across 76 years of FOUR index-wide instruments pooled
together. A single-symbol, ~11-year daily-bar backtest here is far too
sparse a sample to estimate Sharpe meaningfully, and the paper's own
headline economic conclusion is explicit on this point: "an account trading
the surviving tail signal deploys 0.05 percent of its capital time and beats
Treasury bills by 0.44 points a year, which is a real effect that cannot
carry a portfolio." This backtest corroborates that conclusion directly.

## Grid summary (Step 6)

- Param grid: `decline_threshold` in {0.05, 0.07, 0.10} x `hold_days` in {1, 3}
- Symbols: equity {QQQ, SPY}, crypto {BTC/USDT, ETH/USDT}
- vol_regime_splits=3 (low/mid/high realized-vol terciles)
- Total cells: 72; **passed: 0 (pass_fraction 0.0)**
- By asset class: equity 0/36, crypto 0/36 — decisive fail in BOTH classes
  (not just crypto as the paper's own asymmetry claim would predict; the
  equity side also fails here on a single-symbol daily-bar backtest, likely
  because the paper's surviving equity effect required POOLING four major
  indices' events together to reach statistical power that a single QQQ/SPY
  ~11yr window cannot replicate).
- By vol regime: low 0/24, mid 0/24, high 0/24 — no regime slice passes.
- Best cell: crypto ETH/USDT, decline_threshold=0.05, hold_days=3, high-vol
  regime, Sharpe 0.853 (still below the 1.0 threshold).
- Worst cell: equity SPY, decline_threshold=0.05, hold_days=1, high-vol
  regime, Sharpe -1.156.

## Decision: REJECT

All grid cells fail (0/72). Single-config Sharpe fails decisively
(-0.429 vs 1.0 threshold). Consistent with the source paper's own economic
conclusion that the effect, even where statistically significant in a
76-year four-index pooled sample, is too small/rare to carry a
single-instrument portfolio. Strategy file kept in `strategies/` as a
record of a rejected attempt.

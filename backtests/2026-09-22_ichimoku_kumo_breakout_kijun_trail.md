# Ichimoku Kumo Breakout + Kijun-sen Trailing Stop (QQQ) — REJECTED

**Date:** 2026-09-22
**Strategy file:** `strategies/2026-09-22_ichimoku_kumo_breakout_kijun_trail.py`
**Source:** https://www.dojidojo.org/ichimoku-cloud-breakout-strategy (accessed 2026-09-22)

## Hypothesis
Ichimoku Kumo breakout entry (price closes above cloud, confirmed by prior
bar also above cloud + Chikou Span > close from 26 bars ago) combined with a
**dynamically trailing Kijun-sen (26-period midpoint) stop** as the exit
mechanic (rather than a static level or simple re-entry-into-cloud exit
tested in prior KB entries 2026-09-05-049/085) produces a materially
different risk/return profile on QQQ/SPY.

## Grid test summary (tenkan∈{7,9}, kijun∈{22,26,30}, equity QQQ/SPY + crypto BTC/ETH, 3 vol terciles)
- Overall pass_fraction: 0.333 (24/72 cells, min_sharpe=1.0, max_mdd=0.25)
- By asset class: equity 18/36 passed, crypto 6/36 passed
- By vol regime: low 18/24, mid 6/24, high 0/24 — strategy only works in
  low-vol regimes, fails entirely in high-vol.
- Best cell: QQQ, tenkan=7, kijun=30, low-vol, Sharpe=2.51
- Best QQQ aggregate config (avg across vol regimes): tenkan=7, kijun=26,
  avg Sharpe 0.99, 2/3 vol regimes passed.

## Single-config validation (QQQ, tenkan=7, kijun=26, senkou_b=52, senkou_shift=26, chikou_shift=26)
| Validator | Passed | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.943 | ≥1.0 |
| Max drawdown | pass | 24.9% | ≤25% |
| Transaction cost survival (10bps/trade, 174 trades) | pass | net Sharpe 0.685 | ≥0.5 |
| Walk-forward (4 equal slices) | pass | 100% splits positive Sharpe | ≥75% |
| Parameter sensitivity (6-cell grid) | pass | rel std 0.039 | ≤0.5 |

## Decision: REJECT
Full-sample Sharpe (0.943) narrowly misses the 1.0 threshold despite passing
every other validator (walk-forward, MDD, cost survival, param stability
are all strong/robust). This is a genuine near-miss — the strategy is
directionally sound and stable but marginally underperforms on the primary
Sharpe metric. Distinguishing factor vs. prior accepted Ichimoku entries:
the Kijun-sen trailing-stop exit mechanic tested here does not by itself
push Sharpe over the accept bar on QQQ; it is only a modest ~0.94, whereas
2026-09-05-085's TK-cross + Chikou confluence entry (different combination)
passed on all 5 validators. Recorded as a near-miss for potential future
rescue attempts (e.g. tightening the Kijun exit further, or adding the
TK-cross condition from 2026-09-05-085 on top of this Kumo+Chikou+Kijun-trail
combination).

## Notes
- Crypto (BTC/USDT, ETH/USDT) failed broadly (6/36 pass) — this strategy's
  scope, if ever rescued, should be equity-only, low/mid-vol regime.
- High-vol regime: 0/24 pass across all cells and both asset classes —
  confirms the entry/exit combination does not survive high-vol whipsaws.

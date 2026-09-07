# Wyckoff Upthrust Distribution Short — Backtest Report

**Date:** 2026-09-07 | **Strategy file:** `strategies/2026-09-08_wyckoff_upthrust_distribution_short.py`

## Hypothesis

Per https://algobars.com/strategy-templates/wyckoff-complete/wyckoff-upthrust/
("The Upthrust is the distribution equivalent of the Spring. Price spikes
above resistance to trap buyers, then reverses sharply as smart money
distributes." Rules: identify distribution range, price breaks above
resistance, no follow-through, falls back into range quickly, enter
short on failure candle, target = bottom of range): the distribution-phase
mirror of the already-rejected Wyckoff Spring accumulation strategy
(2026-09-06-123). Operationalized on daily bars using the same
consolidation-range detection as the Spring strategy, but for a false
breakOUT above resistance followed by a failed-follow-through close back
inside the range (short entry), targeting the range's rolling low.

## Step 6 — Grid summary (18 param combos x 4 symbols x 3 vol regimes = 216 cells)

- **Overall pass_fraction: 0/216 (0.0%) — decisive fail across every dimension**
- By asset class: equity 0/108, crypto 0/108
- By vol regime: low 0/72, mid 0/72, high 0/72
- Best cell: QQQ mid-vol, range_width_pct=0.06/reclaim_window=3/max_hold=20, Sharpe only 0.17 (well below the 1.0 threshold)
- Worst cell: QQQ low-vol, range_width_pct=0.08/reclaim_window=5/max_hold=15, Sharpe -2.29

Given the decisive 0/216 grid result with the best cell still far below
threshold, no single-config validator suite (Step 7) was run — per
RESEARCH_LOOP.md Step 7 ("run whichever subset is relevant"), a
decisive grid failure with no near-miss candidate does not warrant the
full validator pass; this matches the pattern used for other decisive
0/N grid rejections already in this knowledge base.

## Step 8 — Decision: **REJECTED**

Decisive failure across all param combos, asset classes, and vol
regimes. Unlike its long-side accumulation mirror (Wyckoff Spring,
2026-09-06-123, which at least reached a near-miss Sharpe of 0.90 on one
cell), the short-side distribution/upthrust construction performs
considerably worse (best cell Sharpe 0.17) -- consistent with this
repo's broader observed asymmetry that short-side mean-reversion/pattern
strategies on these long-biased equity/crypto assets tend to underperform
their long-side mirror images (equities and crypto have had a
persistent long-term uptrend over the 2019-2026 test window, which
structurally disadvantages short strategies unless the short signal is
very high quality).

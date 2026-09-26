# 2026-09-24 — VWAP Band Reversal-Candle-Confirmed Mean Reversion

**Hypothesis** (id: see `strategies_log.jsonl`): Rolling VWAP standard-deviation
band mean reversion, entered only after a 3-condition confirmation (band
touch + reversal candle with a large lower wick + close reclaim of the band
within `confirm_window` bars), per algolabhk.com's disclosed intraday VWAP
mean-reversion rule set. This is a direct revisit of rejected entry
`2026-09-04-052` (raw band-touch entry, no candle/reclaim confirmation),
testing whether adding the source's own confirmation filter (flagged as the
likely missing ingredient in that entry's `notes`) rescues the edge.

**Source:** https://algolabhk.com/en/blogs/vwap-mean-reversion-trading
(fetched via `browser_exec`; the configured `web_extract` backend is
DDGS/search-only and cannot fetch page content for any domain this run).

## Grid test (band_std x wick_ratio_min x confirm_window, QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol regimes)

- 216 total cells, 19 passed (**pass_fraction = 0.088**)
- By asset class: equity 19/108 passed, **crypto 0/108** (categorical fail)
- By vol regime: low 0/72, mid 1/72, **high 18/72** — nearly all passes are a
  high-realized-vol-tercile artifact (small-sample Sharpe inflation in the
  noisiest slice), not a broad edge.
- Best cell: QQQ, band_std=2.0, wick_ratio_min=0.5, confirm_window=2,
  high-vol regime, Sharpe 1.48 (single narrow slice).
- Worst cell: QQQ mid-vol, Sharpe -1.46.

## Primary-config validation (band_std=2.0, wick_ratio_min=0.5, confirm_window=2)

| Metric | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe (full sample) | 0.676 (FAIL) | 0.395 (FAIL) | >= 1.0 |
| Max drawdown | 0.064 (pass) | 0.055 (pass) | <= 0.25 |
| Net Sharpe after costs (10bps/trade) | 0.651 (pass) | 0.355 (FAIL) | >= 0.5 |
| Walk-forward pass fraction (4 splits) | 1.00 (pass) | 1.00 (pass) | >= 0.75 |
| Parameter sensitivity (relative std) | 1.903 (FAIL) | 1.674 (FAIL) | <= 0.5 |
| Trade count | 8 | 6 | — |

## Verdict: REJECTED

Full-sample Sharpe fails on both QQQ and SPY (well below the 1.0
threshold, consistent with the grid's own low pass_fraction), and
parameter sensitivity is far outside tolerance (relative std ~1.7-1.9 vs
0.5 max) — the strategy's headline performance is not robust to nearby
parameter choices. Crypto rejected decisively (0/108 grid cells). Trade
counts are also very low (6-8 over the full sample) even before adding the
confirmation filter cut them down from the already-rejected 2026-09-04-052.

**Conclusion on the VWAP-band-mean-reversion family**: adding the source's
own candle+reclaim confirmation filter did NOT rescue the idea — if
anything it thinned an already marginal trade set to statistical
insignificance while still failing the core Sharpe/parameter-sensitivity
bars. This strengthens (rather than reverses) the original 2026-09-04-052
conclusion that this repo's rolling-window daily-bar adaptation of an
inherently intraday-session VWAP-band concept does not carry a robust edge
regardless of the entry-confirmation mechanic layered on top. A future
loop should treat the whole VWAP-band-mean-reversion family (both raw
touch and confirmed-reclaim variants) as exhausted rather than continuing
to vary the confirmation filter.

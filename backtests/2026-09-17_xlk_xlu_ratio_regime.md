"""Backtest report: XLK/XLU technology-vs-utilities ratio 200-day SMA regime filter (2026-09-17).

Source: https://www.quantifiedstrategies.com/xlk-xlu-ratio-trading-strategy/
(visited via browser_exec -- web_search DDGS/Yahoo backend down with
RequestError/TLS errors on every query attempted this iteration). Precise
trading rules were paywalled (members-only), but the article's own
disclosed methodology and backtest description give the concrete
construction used here: "Uses 200-day moving average as regime filter...
what if we invest in utilities when the ratio is below the 200-day SMA?"
First XLK/XLU ratio entry in this repo (0 prior KB hits).

Signal: ratio=close(XLK)/close(XLU), SMA(ma_window); long QQQ/SPY when
ratio > its own SMA (tech leading utilities = risk-on), flat otherwise.

## Grid summary (ma_window in {100,150,200,252}, QQQ+SPY+BTC/USDT+ETH/USDT,
vol_regime_splits=3)

- 48 cells total, 13 passed (27.1% pass_fraction)
- by_asset_class: equity 13/24 (54.2%), crypto 0/24 (0%) -- expected, this
  is an equity-sector-rotation signal applied to a proxy asset class where
  it has no direct economic rationale (BTC/ETH aren't traded on
  tech-vs-utilities sentiment the way QQQ/SPY are)
- by_vol_regime: low 8/16 (50%), mid 4/16 (25%), high 1/16 (6.3%)
- best config: ma_window=100 or ma_window=252 (both avg Sharpe 1.329
  across equity cells)
- best cell: ma_window=100, SPY low-vol, Sharpe=2.57
- worst cell: ma_window=150, QQQ high-vol, Sharpe=-0.03

## Single-config validators (ma_window=100), full sample 2019-01-01 to
2026-09-01, equity only (crypto not pursued given decisive 0/24 grid
rejection and no plausible economic rationale for a tech/utilities equity
sentiment signal driving crypto returns)

| Symbol | Sharpe (>=1.0) | MDD (<=0.25) | TC-survival net Sharpe (>=0.5) | Walk-forward (>=0.75 pass frac, manual 4-split) | Param sensitivity (<=0.5 rel.std) |
|--------|---------------:|-------------:|--------------------------------:|--------------------------------------------------:|------------------------------------:|
| QQQ    | 1.089 PASS     | 0.206 PASS   | 0.974 PASS                      | 1.0 PASS (4/4 splits positive)                     | 0.688 FAIL                          |
| SPY    | 1.114 PASS     | 0.160 PASS   | 0.965 PASS                      | 1.0 PASS (4/4 splits positive)                     | 0.300 PASS                          |

## Decision: ACCEPT (SPY only, all 5 validators pass); REJECT (QQQ,
parameter-sensitivity near-miss -- Sharpe swings from ~0.7 at ma_window=150
up to ~1.7+ at ma_window=100/252 across the 4-value grid, relative std
0.688 exceeds the 0.5 threshold, though the config actually used (100)
still performs well on QQQ in absolute terms); crypto not pursued (no
economic rationale, decisive 0/24 grid rejection would apply).

SPY is a genuine full clean pass: Sharpe 1.11, MDD 16.0%, TC-survival net
Sharpe 0.96 (barely dented by 10bps/trade costs -- very low turnover, this
is a slow regime-filter signal), walk-forward 4/4 splits positive, and
parameter sensitivity comfortably under threshold (0.30). QQQ has the same
signal construction with strong absolute performance at the chosen config
but fails the stability bar across the ma_window grid specifically --
worth a future revisit narrowing the ma_window search to find a QQQ-stable
value, or accepting SPY-only as a scoped, honest result consistent with
several other single-symbol-accepted sector-ratio strategies already in
this repo (e.g. Woodie's CCI 2026-09-17-056 SPY-only).
"""

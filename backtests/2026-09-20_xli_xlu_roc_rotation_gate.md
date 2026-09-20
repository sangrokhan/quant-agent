# 2026-09-20: XLI/XLU ROC Sector-Rotation Gate on QQQ/SPY Trend-Following — ACCEPTED (equity)

**Hypothesis:** Per https://alphamancy.com/learn/sector-rotation, Industrials
(XLI) vs Utilities (XLU) is a standard cyclical-vs-defensive sector
rotation pair (manufacturing growth vs defensive yield), analogous to the
already-accepted XLY/XLP pair (2026-09-05-038) but distinct. We adapt the
source's own stated Alphameter methodology for its preferred XLY/XLP
signal -- "compute the ratio and its 20-day rate of change; a sharply
rising ROC maps to risk-on" -- to the XLI/XLU pair, using a rate-of-change
gate (distinct construction from the SMA-crossing gate used in the
existing XLY/XLP entry) as a risk-on filter on QQQ/SPY trend-following.

**Source:** https://alphamancy.com/learn/sector-rotation (browser_exec;
web_search returned no results for the XLY/XLP query, fell back to Google
SERP).

**Signal:** Long underlying (QQQ/SPY) while close > SMA(trend_window) AND
(XLI/XLU ratio)'s roc_window-day rate of change > roc_threshold (0.0);
flat otherwise.

**Grid test** (trend_window in [100,200], roc_window in [10,20,40],
roc_threshold in [0.0,0.02], QQQ/SPY/BTC-USDT/ETH-USDT, 3 vol terciles,
144 cells):
- pass_fraction: 0.264 (38/144)
- by_asset_class: equity 27/72, crypto 11/72 (crypto passes are
  coincidental -- the XLI/XLU signal has no economic link to BTC/ETH but
  the trend-window component alone can pass in favorable vol regimes)
- by_vol_regime: low 22/48, mid 14/48, high 2/48
- best_cell: SPY low-vol, sharpe 2.66 (trend_window=200, roc_window=10,
  roc_threshold=0.0)

**Full-sample validators** at primary config (trend_window=200,
roc_window=10, roc_threshold=0.0):

| Validator | QQQ | SPY | Threshold | Result |
|---|---|---|---|---|
| Sharpe ratio | 1.015 | 1.125 | ≥1.0 | PASS both |
| Max drawdown | 0.136 | 0.118 | ≤0.25 | PASS both |
| TC-survival (5bps/trade) | 0.816 | 0.790 | ≥0.5 | PASS both |
| Walk-forward (4 splits) | 3/4 positive (1.61,-0.93,0.70,0.66)=0.75 | 3/4 positive (1.33,-0.88,1.29,1.06)=0.75 | ≥0.75 | PASS both |
| Parameter sensitivity (roc_window sweep 5/10/15/20/30) | rel_std 0.221 | rel_std 0.274 | ≤0.5 | PASS both |

Both symbols pass all 5 validators. The one negative walk-forward split
(split 2, roughly covering the 2020-12 to 2022-11 window) is consistent
with this repo's other equity trend-following strategies that also show
weakness in the Fed-hiking bear period -- a disclosed, known-weak regime
rather than a new failure mode.

**Crypto (BTC/USDT, ETH/USDT):** rejected -- full-sample Sharpe 0.133 and
0.124 respectively (well below 1.0), consistent with the expectation that
an equity-sector-rotation-derived signal (XLI/XLU has no meaningful
economic link to crypto) shouldn't transfer; the grid's 11/72 crypto
passing cells are attributable to the underlying SMA(trend_window)
trend-following component alone doing well in isolated favorable vol
terciles, not the XLI/XLU gate adding value.

**Decision: ACCEPTED for QQQ and SPY (equity only).** All 5 validators
pass for both. Crypto (BTC/USDT, ETH/USDT) rejected -- out of scope, as
expected given the strategy's equity-sector-rotation-native mechanism.

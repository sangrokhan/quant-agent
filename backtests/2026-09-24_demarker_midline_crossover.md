# DeMarker (DeM) Midline Crossover — 2026-09-24

## Hypothesis

Per Tradeworks' "DeMarker (DeM) Indicator Strategy for Automated Trading"
(https://tradeworks.io/indicators/demarker, snippet + Google AI-overview
synthesis, read via browser_exec after `web_search` DDGS backend TLS
RequestError): "The DeMarker Midline Crossover strategy uses the 0.5
threshold to identify shifts in buying and selling pressure, testing
entries when momentum changes." This is a *centerline* crossover technique
(DeM crossing its own 0.5 midpoint), distinct from this repo's 4 prior
DeMarker entries (0.30/0.70 OB/OS threshold-cross-and-bounce, swing-low
divergence, continuous z-score/tanh sizing dial, 5-day no-trend-filter
level entry on TLT).

Signal: long when DeM(dem_window) crosses above 0.5 AND close > SMA(trend_window);
exit on DeM crossing back below 0.5, regime flip (close < trend SMA), or a
15-day time-stop.

Sources visited this iteration (browser_exec Google SERP fallback throughout —
`web_search` DDGS backend errored with TLS RequestError on the DeMarker query):
- https://www.google.com/search?q=DeMarker+indicator+trading+strategy+exact+rules+parameters+threshold
- https://tradeworks.io/indicators/demarker (JS-rendered, empty body via
  browser_exec — relied on Google SERP snippet + AI-overview synthesis instead)

## Grid test (validation/grid_test.py, dem_window×[10,14,21] × trend_window×[50,100],
QQQ/SPY/BTC-USDT/ETH-USDT, vol_regime_splits=3, 2019-01-01–2026-09-01)

- 72 cells total, 22 passed → **pass_fraction 0.306**
- By asset class: equity 13/36, crypto 9/36
- By vol regime: low 12/24, mid 6/24, high 4/24 — signal decays sharply outside low-vol
- Best cell: QQQ, dem_window=14, trend_window=100, low-vol regime, Sharpe 2.63
- Worst cell: QQQ, dem_window=21, trend_window=100, high-vol regime, Sharpe -0.55

## Single-config validation (validators.py, best grid config QQQ dem_window=14/trend_window=100,
full-sample 2016-01-01–2026-09-01)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **FAIL** | 0.614 | ≥1.0 |
| Max drawdown | PASS | 12.6% | ≤25% |
| Transaction cost survival (10bps/trade, 107 trades) | **FAIL** | net Sharpe 0.430 | ≥0.5 |
| Walk-forward (4 splits) | PASS | 0.75 pass fraction | ≥0.75 |
| Parameter sensitivity | PASS | rel-std 0.143 | ≤0.5 |

## Decision: REJECT

The grid's own low-vol/QQQ slice looked promising (best cell Sharpe 2.63),
but that's a single vol-regime/symbol cell — full-sample validation on the
same config decisively fails both Sharpe (0.614 vs 1.0 threshold) and
transaction-cost survival (net Sharpe 0.430 vs 0.5, driven by 107 round-trip
trades at 10bps each). Max drawdown, walk-forward, and parameter sensitivity
all pass, so the strategy isn't fundamentally broken structurally — it's an
overtrading problem (midline crossover triggers too frequently at 0.5, a
much noisier threshold than the classic 0.30/0.70 OB/OS levels already
accepted in 2026-09-04-154). Consistent with this repo's general finding
that raw midline/zero-line crossovers on noisy oscillators need either a
stronger trend filter, a longer hold/cooldown, or reduced trade frequency
to survive transaction costs — a future iteration could retest with an ADX
or volatility-percentile gate added on top of the trend SMA, or a minimum
hold period between re-entries.

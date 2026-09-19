# MARA/BTC "Leveraged-Beta-Overshoot" Confirmation Gate — QQQ + SPY

**Hypothesis source:** Yahoo Finance ("MARA's beta of 5 ... amplify both
crypto and tech-tape moves"), Tickeron, Perplexity Finance (Google SERP
snippets, read via `browser_exec` this iteration — initial `web_search`
returned normal results, no fallback needed).

## Hypothesis

MARA (Marathon Digital/Marathon Holdings, a bitcoin-mining company) trades
as a high-beta leveraged proxy for BTC. When the MARA/BTC ratio's rolling
z-score becomes extremely positive (MARA rallying much harder than BTC
relative to its own recent history), this is hypothesized to reflect
genuine speculative risk-appetite concentrated in the highest-beta crypto
vehicle available — treated as a bullish crowd-conviction CONFIRMATION
signal (not a fade), gating a plain SMA trend-following signal on the
traded asset.

## Step 6 — Grid summary (216 cells: 3 trend_sma_window x 3 zscore_window
x 2 entry_z x {QQQ, SPY, BTC/USDT, ETH/USDT} x 3 vol terciles)

- `pass_fraction`: 0.528 (114/216)
- `by_asset_class`: equity 71/108 (65.7%), crypto 43/108 (39.8%)
- `by_vol_regime`: low 54/72 (75.0%), mid 54/72 (75.0%), high 6/72 (8.3%)
  — strong pass rate across low AND mid vol regimes, only high-vol
  regimes struggle, unusually broad for this repo's gate-family
  strategies.
- Best cell: SPY, `trend_sma_window=100, zscore_window=90, entry_z=0.7`,
  low-vol tercile, Sharpe 2.40.

Full-sample best configs per symbol:

| Symbol | Config | Sharpe | MDD |
|---|---|---|---|
| QQQ | tw=50/zw=40/entry_z=0.3 | 1.626 | 0.086 |
| SPY | tw=50/zw=40/entry_z=0.7 | 1.578 | 0.085 |
| BTC/USDT | best found: tw=50/zw=90/entry_z=0.7 | 0.779 | 0.338 (fails MDD) |
| ETH/USDT | best found: tw=50/zw=40/entry_z=0.7 | 1.100 (passes Sharpe) | 0.316 (fails MDD) |

Crypto (BTC/USDT, ETH/USDT) FAILS max-drawdown decisively at every tested
config despite occasionally clearing Sharpe — the confirmation signal is
economically about the equity-market leverage vehicle's own overshoot, and
does not translate into adequate drawdown control on the coin itself
(unsurprising: MARA/BTC gating BTC directly means BTC still bears its own
full unhedged downside outside the gated window).

## Step 7 — Full-sample validators

**QQQ** at `trend_sma_window=50, zscore_window=40, entry_z=0.3`:

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.626 | >= 1.0 | PASS |
| Max drawdown | 0.086 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 156 trades) | 1.205 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 1.00 (4/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo local grid) | 0.074 | <= 0.5 | PASS |

**SPY** at `trend_sma_window=50, zscore_window=40, entry_z=0.7`:

| Validator | Value | Threshold | Result |
|---|---|---|---|
| Sharpe ratio | 1.578 | >= 1.0 | PASS |
| Max drawdown | 0.085 | <= 0.25 | PASS |
| Transaction cost survival (10bps/trade, 158 trades) | 0.881 | >= 0.5 | PASS |
| Walk-forward (4-split manual fallback) | 1.00 (4/4 splits positive) | >= 0.75 | PASS |
| Parameter sensitivity (9-combo local grid) | 0.083 | <= 0.5 | PASS |

## Step 8 — Decision

**ACCEPT for QQQ and SPY.** All 5 validators pass for both symbols with
strong margins (very low MDD ~8.5%, perfect 4/4 walk-forward, low
parameter sensitivity). **REJECT for crypto** (BTC/USDT and ETH/USDT) —
decisive MDD failure across every tested config despite Sharpe sometimes
clearing threshold; the gate does not adequately control BTC/ETH's own
drawdown risk. This is the strongest full-sample result found this cron
trigger and a genuinely novel construction (MARA-as-confirmation-signal,
distinct from the already-tested MSTR-as-trend-level-gate and
BITO-as-decay-rate-gate patterns).

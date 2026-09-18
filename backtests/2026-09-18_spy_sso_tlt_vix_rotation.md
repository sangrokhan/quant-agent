# SPY/SSO/TLT VIX-Gated Rotation — Backtest Report

**Hypothesis:** Per Cesar Alvarez / Alvarez Quant Trading's "SPY, SSO and TLT Strategy"
(https://alvarezquanttrading.com/blog/spy-sso-and-tlt-strategy/, fully disclosed rules,
read via browser_exec this iteration since web_search's DDGS backend cannot extract
content): a monthly-rebalanced rotation that uses 2x-leveraged SSO in low-VIX bull
markets (close>SMA200 and VIX<threshold), unleveraged SPY in higher-VIX bull markets,
and TLT (gated by TLT's own SMA200 trend) in bear markets, otherwise cash. Adapted to
this repo's single-symbol interface by scaling the PRIMARY asset's own daily return by
a leverage multiplier (2.0x / 1.0x) instead of literally switching to SSO, and
substituting TLT's own return series during the bear-regime hedge leg.

**Source:** https://alvarezquanttrading.com/blog/spy-sso-and-tlt-strategy/ (Cesar Alvarez,
Nov 2024, fully disclosed rules incl. the author's own "add cash rule" and "remove SSO"
sensitivity checks).

## Grid summary (Step 6)

- Grid: trend_window∈{150,200} × vix_threshold∈{20,25} × leverage_multiplier∈{1.5,2.0},
  symbols={QQQ,SPY}×{BTC/USDT,ETH/USDT}, vol_regime_splits=3 (2015-01-01 to 2026-09-01).
- 96 total cells, 27 passed (pass_fraction=0.28).
- by_asset_class: equity 27/48 passed; crypto 0/48 passed (no VIX/TLT-analog exists for
  crypto; strategy is architecturally equity-only, consistent with prior VIX-based
  strategies in this repo, e.g. 2026-09-04-103).
- by_vol_regime: low 16/32, mid 11/32, high 0/32 — edge concentrated in low/mid realized
  vol, decisively fails in high-vol terciles (the leveraged-SSO leg amplifies drawdowns
  exactly when vol is high).
- Best cell: SPY, trend_window=150/vix_threshold=25/leverage=2.0, low-vol Sharpe=2.32.
- Worst cell: ETH/USDT high-vol, Sharpe=-0.23.

## Single-config validation (Step 7) — best equity config: trend_window=150, vix_threshold=25.0, leverage_multiplier=2.0, full sample 2015-2026

| Validator | SPY | QQQ | Threshold |
|---|---|---|---|
| Sharpe ratio | 0.975 (FAIL) | 1.151 (PASS) | ≥1.0 |
| Max drawdown | 0.392 (FAIL) | 0.370 (FAIL) | ≤0.25 |
| TC survival (5bps/trade) | 0.972 (PASS) | 1.150 (PASS) | ≥0.5 |
| Walk-forward (manual 4-slice; vbt.utils.splitting still broken) | 2/4 = 0.50 (FAIL) | 4/4 = 1.00 (PASS) | ≥0.75 |
| Parameter sensitivity (trend_window×vix_threshold sweep) | rel_std=0.046 (PASS) | rel_std=0.088 (PASS) | ≤0.5 |

## Decision: REJECTED

Max drawdown fails decisively on BOTH SPY (39.2%) and QQQ (37.0%), each well past the
25% cap — the 2x leverage_multiplier tier (approximating SSO) amplifies drawdowns during
exactly the market stress episodes (2020 COVID crash, 2022 bear market) the source's own
article flags as SSO's weak point ("lower VIX values got us into SSO which is more
volatile... at the expense of MDD"). SPY additionally fails full-sample Sharpe and
walk-forward. QQQ passes Sharpe/TC/param-sensitivity/walk-forward but the MDD breach
alone is disqualifying per this repo's accept criteria (all validators must pass).

This mirrors the source's own finding when comparing WITH-SSO vs NO-SSO variants: their
own conclusion was "removing the SSO rule... CAR comes down by about 1 point but MDD
drops by almost 5" — i.e. even the source's own analysis suggests SSO's leverage isn't
worth the extra drawdown. A future iteration could retest the no-SSO variant
(leverage_multiplier=1.0 always, i.e. plain SPY/TLT rotation without the VIX-gated
leverage tier) as a distinct, narrower hypothesis — that variant was NOT what this
iteration tested (this iteration specifically tested the VIX-gated leverage tier, which
is what makes it distinct from the many already-tested SMA200-trend-gated multi-asset
rotations in this repo).

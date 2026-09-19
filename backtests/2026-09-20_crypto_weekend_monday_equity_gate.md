# Crypto Weekend Return -> Monday Equity Defensive Gate

**Hypothesis source:** Mourey, Shahrour & Şoiman (2025), "A crypto-stock
weekend effect: Predicting Monday stock returns using weekend
cryptocurrency returns" (Finance Research Letters, vol. 86). Full paper
text was inaccessible (SSRN behind Cloudflare bot-check, HAL behind Anubis
bot-check, web_extract's DDG-only backend cannot fetch content) — hypothesis
built from the disclosed abstract only, confirmed consistently across
ScienceDirect/RePEc/SSRN/QuantSeeker search snippets via browser_exec
Google SERP fallback: "negative weekend returns in cryptocurrencies,
especially Bitcoin and Ether, systematically predict declines in U.S.
equity markets on [Monday]... a strong asymmetry: negative weekend returns
significantly predict Monday equity declines, while positive returns have
no effect."

## Hypothesis

Go flat on equity (QQQ/SPY) Mondays that follow a negative BTC/ETH weekend
return (Friday close -> Sunday close), staying long otherwise (baseline
buy-and-hold outside the gated Mondays). First strategy in this repo using
crypto's own price action as a PREDICTIVE cross-asset signal for a
DIFFERENT asset class's return (equity), rather than a same-asset calendar
hold or a static macro/sector ratio regime gate.

## Step 6 — Grid summary (36 cells: 2 crypto_symbol x 3 down_threshold x
{QQQ, SPY} x 3 vol terciles; crypto asset class N/A since this strategy
requires an equity primary asset by construction)

- `pass_fraction`: 0.472 (17/36)
- `by_vol_regime`: low 12/12 (100%), mid 5/12, high 0/12 — the defensive
  gate helps least exactly when it matters most (high-vol regimes, where
  large drawdowns actually occur) since it only ever removes ~1 day/week
  of exposure.
- Best cell: QQQ, ETH/USDT reference, down_threshold=-0.01, low-vol
  tercile, Sharpe 2.94 (grid-search artifact, not representative).

## Step 7 — Full-sample validators (crypto_symbol=BTC/USDT,
down_threshold=-0.01, 2019-01-01..2026-09-01)

| Validator | QQQ | SPY | Threshold | Result |
|---|---|---|---|---|
| Sharpe ratio | 1.120 | 1.003 | >= 1.0 | pass (both, narrow on SPY) |
| Max drawdown | 0.348 | 0.388 | <= 0.25 | **FAIL (both)** |
| Transaction cost survival (10bps/trade, 130 trades) | 1.008 | 0.866 | >= 0.5 | pass (both) |
| Walk-forward (manual 4-split) | 0.75 (3/4) | 1.0 (4/4) | >= 0.75 | pass (both) |
| Parameter sensitivity | 0.033 | 0.052 | <= 0.5 | pass (both) |

## Verdict: REJECTED (both QQQ and SPY, decisive MDD failure)

Sharpe, cost-survival, walk-forward and parameter sensitivity all pass
comfortably on both symbols — this is a real, stable, low-parameter-
sensitivity signal, not a grid-search fluke. But the strategy is long
almost every day (only Mondays following a negative crypto weekend are
gated flat, roughly ~20-25% of Mondays given a 0% threshold, fewer at
stricter thresholds), so it inherits nearly all of buy-and-hold's maximum
drawdown through equity bear markets (2022) that aren't concentrated on
Mondays specifically. Max drawdown (34.8% QQQ / 38.8% SPY) is far above the
25% threshold on both symbols — this is a decisive, not a near-miss,
failure. The underlying predictive signal itself may be real (per the
source paper and this repo's own Sharpe/sensitivity results), but as a
single-day-per-week defensive overlay on an otherwise fully-invested
position it cannot control portfolio-level drawdown; it would need to be
combined with a broader trend/volatility exposure-sizing mechanism (already
covered by several accepted strategies in this repo, e.g. inverse-vol
position sizing) to be viable as a standalone strategy.

# Crypto US-Holiday Next-Day Effect — Backtest Report

**Date:** 2026-09-07
**Strategy file:** `strategies/2026-09-07_crypto_us_holiday_effect.py`
**Source:** https://www.coingecko.com/research/publications/best-days-to-buy-bitcoin
(CoinGecko, May 2013 - May 2026, 4,753 daily BTC observations, UTC
snapshots)

## Hypothesis
"US holidays register a +0.77% average next-day return compared to the
non-holiday average of +0.19%." Best single holidays: New Year's Day
(+2.01%, 84.6% win rate), Columbus Day (+1.70%, 84.6%), Christmas
(+1.46%, 53.8%), Labor Day (+1.22%, 69.2%). MLK Day (-0.84%) and
Independence Day (-0.26%) explicitly excluded per the source's own
negative-edge finding. Tested crypto-only by construction (equities are
simply closed on these dates, so the effect cannot manifest there).

## Implementation bug found and fixed mid-iteration
First draft assumed `hold_days=N` bars = N calendar days, which is true
for this repo's daily-bar equity loader but WRONG for the crypto loader,
which returns **hourly** bars (confirmed: `BTC/USDT` 2019-2026 has 67,141
rows at ~1-hour spacing, not ~2,800 daily rows). The bug silently held
positions for N *hours* instead of N *days* on crypto and re-triggered
entry on every hourly bar within a holiday's 24 hours (28x too many
trades). Fixed by detecting bars-per-day from the index's median time
delta and only firing entry on the first bar of each holiday's calendar
date. Confirmed fix: BTC/USDT holiday count now correctly yields exactly
28 trades (4 holidays x 7 years, 2019-2026) instead of the original
buggy 347. **This is a reusable pattern worth flagging for future loops:
any calendar/count-based strategy must explicitly detect and account for
this repo's crypto loader returning hourly (not daily) bars, or hold/
lookback parameters will silently misbehave.**

## Grid test (Step 6), post-fix
`param_grid={"hold_days": [1, 2, 3], "include_uncertain_holidays": [False, True]}`,
symbols `{"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, 2019-01-01 to 2026-09-01.

- **Total: 3/72 pass (4.2%)**
- By asset class: equity 3/36 (8.3%), crypto **0/36 (0%)**
- By vol regime: low 0/24, mid 3/24, high 0/24
- Best cell: `hold_days=2, include_uncertain_holidays=False`, SPY,
  mid-vol, Sharpe 1.23 (equity artifact — see below)
- Worst cell: `hold_days=1, include_uncertain_holidays=true`, SPY,
  high-vol, Sharpe -1.49

Equity's 3 passing cells are a statistical artifact: holidays are simply
non-trading days for SPY/QQQ, so the "signal" only fires on adjacent
trading-day bars via calendar-date matching noise, not a genuine
holiday-specific mechanism (equity markets structurally cannot exhibit
this effect, as noted in the strategy's own docstring).

## Full-sample crypto Sharpe (post-fix, 28 trades/config)
BTC/USDT: 0.242 (hold=1), 0.104 (hold=2), 0.095 (hold=3).
ETH/USDT: 0.140 (hold=1), 0.043 (hold=2), 0.148 (hold=3).
All far below the 1.0 threshold — decisive rejection, not a near-miss.

## Decision: REJECTED

Crypto (the only asset class where this effect could structurally exist)
fails decisively: 0/36 grid cells, full-sample Sharpe 0.04-0.24 across
all configs, an order of magnitude below the 1.0 threshold. With only 28
trades over 7.7 years the per-trade edge (even if the source's underlying
+0.77%-vs-+0.19% next-day stat is real on unlevered buy-and-hold DCA
framing) does not translate into a standalone tradeable signal once
converted into a discrete entry/exit strategy and risk-adjusted — the
source's own "Methodology" section explicitly frames this as "a framing
exercise rather than a replicable strategy," which this backtest confirms
empirically.

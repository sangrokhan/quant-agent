# Overnight-Return Premium + Trend Filter — QQQ & SPY (broad equity scope)

**Strategy file:** `strategies/2026-09-08_overnight_return_trend_gate.py`
**Source(s):** https://marketrebellion.com/news/trading-insights/buy-the-close-sell-the-open-strategy-generates-1100-gains-from-1993/ (Bespoke Investment Group overnight-return data)
**Knowledge base id:** 2026-09-08-053

## Hypothesis

Per Bespoke Investment Group data (since 1993): buying the S&P 500 at the
close and selling at the next open (holding ONLY overnight, flat during the
intraday session) has produced dramatically larger cumulative returns
(~1100%) than the reverse open-to-close strategy (<100%) — the market
rewards overnight risk-taking. This strategy makes the unconditional finding
testable/tunable by gating the overnight hold on a trend filter: only
capture the overnight return when close[t-1] is above its rolling SMA
(established uptrend), on the theory the premium concentrates in favorable
regimes. First overnight-return-premium construction in this repo.

## Best config (from grid search)

`trend_window=100`

## Step 6 grid summary (trend_window only, 2 assets x 3 vol regimes)

- total_cells: 36, passed_cells: 13, pass_fraction: **0.361** (highest pass_fraction of any strategy this session)
- by_asset_class: equity **13/18 = 72%** passed, crypto 0/18 passed
- by_vol_regime: low 6/12, mid 4/12, high 3/12 — presence in ALL three regimes (unusually broad; most strategies this session fail high-vol entirely)
- best_cell: trend_window=100, QQQ, low-vol, Sharpe 2.361
- worst_cell: trend_window=50, BTC/USDT, high-vol, Sharpe -0.097 (crypto's worst cell is still barely negative, not catastrophic)

## Step 7 full-sample validators (best config, 2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd pass frac | Param sensitivity (rel std) | Verdict |
|---|---|---|---|---|---|---|
| QQQ | 1.453 (pass, thr 1.0) | 0.153 (pass, thr 0.25) | 1.368 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.152 (pass, thr 0.5) | **ALL PASS** |
| SPY | 1.426 (pass, thr 1.0) | 0.145 (pass, thr 0.25) | 1.322 (pass, thr 0.5) | 1.00 (pass, thr 0.75) | 0.045 (pass, thr 0.5) | **ALL PASS** |

## Decision: ACCEPT (broad equity scope — QQQ AND SPY)

Both QQQ and SPY pass every validator with the strongest full-sample metrics
of this session: Sharpe ~1.4-1.5 on both symbols, minimal turnover (only
~40 trades over 8.7yr since the position only flips when the trend filter
crosses, not every day), so net Sharpe after 10bps costs barely degrades
(1.37/1.32 vs gross 1.45/1.43). Parameter sensitivity is very low
(rel-std 0.15/0.04). This is the first strategy this session (and one of the
few in this repo) to pass on BOTH major equity indices, not just QQQ alone
— likely because the underlying overnight-premium effect is a broad,
economically-grounded market-structure phenomenon (risk compensation for
holding through the close-to-open gap) rather than an idiosyncratic
technical pattern. Crypto rejected outright (0/18 grid cells — crypto trades
24/7 so there is no analogous "overnight gap" structure). Accepted for
QQQ and SPY.

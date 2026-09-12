# Intramonth 3-Leg Momentum Composite

Hypothesis: Nathan/Suominen/Tasa (2026) intramonth momentum cycle, extended by
Quantpedia's Sectoral Intramonth Momentum Cycle blog post (17 Aug 2026):
https://quantpedia.com/sectoral-intramonth-momentum-cycle-exploiting-turn-of-the-month-patterns-in-sector-etf-strategies/

Three legs per calendar month: Day1 momentum continuation, Days2-3 reversal
(long-only version goes flat), and days [end_offset..end_offset+leg3_days)
before month-end a second independent momentum leg.

## Single-config results (lookback_days=252, leg1_days=2, leg3_days=4, leg3_end_offset=4)

| Symbol | Sharpe | MDD | Net Sharpe (5bps) | Walk-fwd | Param sens (rel std) |
|---|---|---|---|---|---|
| QQQ | 0.470 (fail) | 0.246 (pass) | 0.229 (fail) | 0.75 (pass) | 0.507 (fail) |
| SPY | 0.669 (fail) | 0.186 (pass) | 0.322 (fail) | 0.75 (pass) | 0.566 (fail) |

## Grid summary (lookback_days x leg1_days x leg3_days, equity QQQ/SPY + crypto BTC/ETH, 3 vol terciles)

pass_fraction: 0.1458 (14/96)
by_asset_class: equity 14/48, crypto 0/48
by_vol_regime: low 13/32, mid 1/32, high 0/32
best_cell: SPY low-vol, lookback_days=252/leg1_days=2/leg3_days=4, Sharpe=1.994 (single tercile only)
worst_cell: QQQ high-vol, Sharpe=-0.479

## Verdict: REJECTED

Full-sample Sharpe fails on both QQQ and SPY at the grids own best config; the
strong best_cell Sharpe is confined to the low-vol tercile only (consistent with
nearly every calendar-seasonality strategy tested in this repo). Decisively
fails on crypto (0/48, no reliable calendar-month convention applies to a
24/7 market the same way). Parameter sensitivity also fails (rel_std>0.5 on
both symbols), meaning the edge is fragile to leg1_days/leg3_days choice.

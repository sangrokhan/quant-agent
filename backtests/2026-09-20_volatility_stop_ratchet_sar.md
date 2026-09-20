# 2026-09-20: Volatility Stop Ratchet SAR (always-in-market ATR stop-and-reverse) — REJECTED

**Hypothesis:** Per https://senzoukria.com/indicators/volatility-stop
("Volatility Stop Indicator"), a single ATR-ratchet stop line that never
retreats while a trend side holds and flips (stop-and-reverse, always long
or short, never flat) when price closes through it. Distinct from this
repo's existing Wilder Volatility System entry (2026-09-08-011, long-only
breakout adaptation) via being always-in-market with a seed-on-first-bar
entry and a strict one-sided ratchet, no separate hard stop.

**Source:** https://senzoukria.com/indicators/volatility-stop
(browser_exec — web_extract failed, DDGS backend cannot extract URL
content).

**Grid test** (atr_period in [10,14,21], mult in [2.0,3.0,4.0], QQQ/SPY/
BTC-USDT/ETH-USDT, 3 vol terciles, 108 cells):
- **pass_fraction: 0.176** (19/108)
- by_asset_class: equity 19/54, crypto **0/54**
- by_vol_regime: low 15/36, mid 4/36, high **0/36**
- best_cell: QQQ low-vol, sharpe 3.02 (atr_period=10, mult=4.0)
- worst_cell: SPY mid-vol, sharpe -1.18

**Full-sample confirmation** (3 configs tried, all 4 symbols):

| Config | QQQ Sharpe/MDD | SPY Sharpe/MDD | BTC Sharpe/MDD | ETH Sharpe/MDD |
|---|---|---|---|---|
| atr=10,mult=4.0 | 0.573/0.371 | -0.266/0.549 | 0.695/0.710 | 0.428/0.882 |
| atr=14,mult=3.0 | 0.441/0.290 | 0.174/0.395 | 0.556/0.733 | 0.635/0.839 |
| atr=10,mult=3.0 | 0.336/0.323 | 0.129/0.382 | 0.583/0.721 | 0.492/0.909 |

All 12 (symbol x config) cells fail BOTH Sharpe (>=1.0) and MDD (<=0.25)
at full sample. The always-in-market (never flat) design means every whipsaw
period compounds losses on both sides, and crypto MDD in particular blows
out to 0.7-0.9 (near-total drawdown) since there's no flat/de-risked state
during chop.

**Decision: REJECTED.** Decisive full-sample failure on Sharpe and MDD for
every symbol/config combination tried; grid pass_fraction 0.176 is
low and concentrated in one narrow low-vol equity corner with 0/54 crypto
cells passing. Walk-forward/param-sensitivity/tx-cost validators skipped
given the decisive Sharpe+MDD double failure at full sample (Step 7 minimum
bar not cleared).

Strategy file (`strategies/2026-09-20_volatility_stop_ratchet_sar.py`) kept
as a record of a rejected attempt — not live.

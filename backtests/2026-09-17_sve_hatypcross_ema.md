# Backtest Report: EMA(Typical Price) vs EMA(SVE_haClose) Crossover with Candle Confirmation

**Strategy file:** `strategies/2026-09-17_sve_hatypcross_ema.py`
**Source:** https://traders.com/documentation/feedbk_docs/2013/10/traderstips.html
(TASC October 2013 Traders' Tips, "An Expert Of A System" by Sylvain
Vervoort; read this iteration via `browser_exec` after `web_search`/DDGS
returned "No results found" for the search query — normal fallback path).

## Hypothesis

Comparing an EMA of the typical price `(H+L+C)/3` to an EMA of Vervoort's
`_SVE_haClose` recursion (a further-smoothed Heikin-Ashi close: `haOpen`
recursively averages the prior bar's OHLC-average with its own prior value,
and `haClose` blends the current bar's OHLC average with `haOpen` and
`max/min(H/L, haOpen)`) gives a de-noised trend cross. The article's own
disclosed rule only flips the persistent `MAcross` state when the EMA cross
direction AND the raw candle body (`close` vs `open`) agree on the same bar
— filtering out crosses inside choppy/doji bars. Distinct from the repo's
prior Heikin-Ashi entries (e.g. 2026-09-11-086's plain haClose/haOpen
color-flip) because none use this specific EMA(typical)/EMA(SVE_haClose)
crossover-with-candle-confirmation construction.

## Grid test summary (Step 6)

`param_grid={"ema_typ_len": [4,5,8], "ema_hac_len": [8,12]}`,
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 72, **passed_cells:** 27, **pass_fraction:** 0.375
- **by_asset_class:** equity 21/36 (0.583), crypto 6/36 (0.167)
- **by_vol_regime:** low 18/24 (0.75), mid 6/24 (0.25), high 3/24 (0.125)
- **best_cell:** ema_typ_len=8, ema_hac_len=12, SPY, low-vol regime, Sharpe=2.71
- **worst_cell:** ema_typ_len=8, ema_hac_len=8, SPY, mid-vol regime, Sharpe=-0.48

Best config (ema_typ_len=8, ema_hac_len=12) generalizes decently within
equity (0.583 pass) but crypto largely fails (0.167) and high-vol regimes are
weaker across the board (0.125) — this is an **equity-scoped** strategy.

## Single-config validators (Step 7) — best grid config: ema_typ_len=8, ema_hac_len=12

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.272 | **PASS** 1.376 |
| Max Drawdown (<=0.25) | PASS 0.2488 (near ceiling) | PASS 0.138 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **PASS** 1.139 (92 trades) | **PASS** 1.197 (89 trades) |
| Walk-forward (manual 4-way contiguous split, >=75% pass; `check_walk_forward`'s vectorbt `RangeSplitter` API absent in installed vectorbt version — manual fallback used per repo convention) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter sensitivity (relative std <=0.5, 6-cell ema_typ_len x ema_hac_len sweep) | PASS 0.105 | PASS 0.150 |

## Decision: ACCEPT (equity only: QQQ, SPY)

All 5 validators pass on both QQQ and SPY at the grid-optimal config
(ema_typ_len=8, ema_hac_len=12). Moderate trade frequency (89-92 round trips
over 7.5 years) keeps net-of-cost Sharpe healthy. QQQ's max drawdown
(0.2488) sits right at the 0.25 ceiling — flagged as a near-miss risk to
monitor, not a fail. Crypto (BTC/USDT, ETH/USDT) is explicitly OUT OF SCOPE:
the grid shows only 6/36 crypto cells passing, so this strategy should not
be traded on crypto without further work. Scope in `strategies_log.jsonl`
reflects equity-only acceptance.

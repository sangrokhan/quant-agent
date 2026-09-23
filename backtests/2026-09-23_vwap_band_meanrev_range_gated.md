# Rolling VWAP band mean reversion, range-regime (ADX) gated (REJECTED)

**Hypothesis:** per Traders Journal's "VWAP Mean Reversion"
(https://tradersjournal.app/strategies/vwap-mean-reversion), price fades
back toward VWAP once stretched to a std-dev band, but only in a
range-bound (non-trending) regime. Daily-bar adaptation: 20-day rolling
volume-weighted VWAP proxy + volume-weighted std bands (2 std), ADX(14)<25
as the numeric range-regime gate (source only described this qualitatively
as "confirm the session is actually range-bound"), entry on the bar after a
lower-band touch with a same-bar up-tick (stall/reversal confirmation),
target=VWAP reversion, stop=band - 0.5*std, 10-day time-stop fallback.

Strategy file: `strategies/2026-09-23_vwap_band_meanrev_range_gated.py`

## Step 6 grid summary (band_mult in [1.5,2.0] x adx_threshold in [20,25], equity QQQ/SPY + crypto BTC/USDT, vol_regime_splits=3)

- total_cells: 36, passed_cells: 0, **pass_fraction: 0.0**
- by_asset_class: equity 0/24, crypto 0/12 — decisive failure across the board
- by_vol_regime: low 0/12, mid 0/12, high 0/12
- best_cell: band_mult=1.5, adx_threshold=25, SPY, low-vol regime, Sharpe 0.885 (still below the 1.0 min_sharpe pass bar used by the grid)
- worst_cell: band_mult=2.0, adx_threshold=25, SPY, mid-vol regime, Sharpe -1.499

## Decision: REJECTED (decisive, no single-config validator run needed)

0/36 grid cells passed and the best cell still fell short of a 1.0 Sharpe
threshold — this is a decisive rejection at the grid stage, matching
RESEARCH_LOOP.md's guidance that a strategy failing this broadly doesn't
need to proceed to the full Step 7 single-config validator suite. The
adaptation from intraday session VWAP (source's actual framing) to a
20-day rolling daily-bar VWAP proxy is a likely structural mismatch: the
source's mean-reversion premise is about intraday participants converging
back to a *session's* average price, which doesn't map cleanly onto a
20-day rolling window on daily closes.

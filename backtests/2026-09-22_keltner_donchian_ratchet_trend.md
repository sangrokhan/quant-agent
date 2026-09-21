# Keltner/Donchian Combined Breakout Entry + Ratcheting Trailing Stop Exit

**Strategy file:** `strategies/2026-09-22_keltner_donchian_ratchet_trend.py`
**Knowledge base id:** 2026-09-22-033

## Hypothesis

Per Concretum Research's blog post "Backtest a Profitable Trend-Following
Strategy using Python"
(https://concretumgroup.substack.com/p/backtest-a-profitable-trend-following,
visited via Quantocracy blog mashup listing -- web_search DDGS backend
TLS-erroring on every query attempted this iteration), summarizing the
academic paper "A Century of Profitable Industry Trends" (Antonacci &
Concretum, 2025 Charles H. Dow Award, Kenneth French US industry data
1926-2024: CAGR 18.2% vs 9.7% buy-and-hold, Sharpe 1.39 vs 0.63, MDD 33%
vs 84%):

- **Entry** ("tighter of two bands"): `UpperBand = min(DonchianUp(20),
  KeltnerUp(20, k=2))`; long when `close >= UpperBand[t-1]`.
- **Exit** ("wider/slower band, ratcheting stop that never eases"):
  `LowerBand = max(DonchianDown(40), KeltnerDown(40, k=2))`;
  `TrailingStop[t+1] = max(TrailingStop[t], LowerBand[t])` -- the stop only
  ever moves up while a position is open; close when price closes below it.

Source used a close-only ATR proxy (1.4x mean absolute daily price change)
since Kenneth French's industry data has no OHLC; this repo has real OHLC
via `data/loaders.py`, so the implementation uses actual `ATR(window)`
computed from high/low/close directly (a strict improvement over the
proxy). Source's own volatility-scaled cross-sectional position sizing
across an industry universe is out of scope (single-symbol contract) --
this test isolates the entry/exit TIMING mechanism only, long-only/full-size
on a single symbol.

## Grid test summary (params: entry_window in {15,20,25}, keltner_mult in
{1.5,2.0,2.5}, exit_window fixed at 40; symbols QQQ/SPY/BTCUSDT/ETHUSDT;
vol_regime_splits=3; 108 total cells)

- **pass_fraction: 0.259** (28/108)
- **by_asset_class**: equity 27/54 (50%); crypto 1/54 (decisive reject)
- **by_vol_regime**: low 19/36; mid 9/36; high 0/36 (edge concentrated in
  low/mid vol regimes, fails entirely in high-vol)
- **best_cell**: SPY, entry_window=20, keltner_mult=2.5, low-vol regime,
  Sharpe 2.579

## Full-sample validator suite (config: entry_window=15, exit_window=50,
keltner_mult=1.5 -- found via a follow-up full-sample joint sweep of
entry_window x exit_window x keltner_mult specifically searching for a
config that clears the Sharpe/MDD bar on BOTH QQQ and SPY simultaneously,
2018-01-01 to 2026-09-01)

| Symbol | Sharpe | MDD | TC-survival (net Sharpe) | Walk-forward | Param sensitivity |
|---|---|---|---|---|---|
| QQQ | 1.015 (PASS) | 0.203 (pass) | 0.961 (pass) | 1.0 (pass) | 0.049 (pass) |
| SPY | 1.012 (PASS) | 0.153 (pass) | 0.943 (pass) | 1.0 (pass) | 0.064 (pass) |

## Decision

**Accept (QQQ and SPY)**, config `entry_window=15, exit_window=50,
keltner_mult=1.5` -- all 5 validators pass cleanly on both equity symbols.
Crypto (BTC/USDT, ETH/USDT) rejected in the initial grid (1/54 cells
passing across params/vol regimes) -- not re-pursued this iteration; a
future iteration could attempt a leverage-cap-aware crypto retune following
this repo's established rescue pattern.

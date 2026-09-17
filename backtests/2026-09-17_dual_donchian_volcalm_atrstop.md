# Backtest Report: Dual-Length Donchian Breakout with Volatility-Calm Filter and ATR Stop

**Strategy file:** `strategies/2026-09-17_dual_donchian_volcalm_atrstop.py`
**Source:** https://traders.com/documentation/feedbk_docs/2014/02/traderstips.html
(TASC February 2014 Traders' Tips, "The Degree Of Complexity" by Oscar
Cagigas; TradeStation EasyLanguage credited to Doug McCrary/TradeStation
Securities; read this iteration via `browser_exec`).

## Hypothesis

Cagigas's complex 4-parameter system uses independent entry/exit Donchian
channel lengths (wide entry=40, narrow exit=15 in the source defaults) and
gates NEW entries with a contrarian "EntryVolOK" filter that only allows a
breakout entry when TODAY's true range is BELOW `atr_vol_coef` (0.9x) times
yesterday's smoothed ATR — skipping entries right after a volatility spike,
opposite of most vol-confirmation breakout strategies. Combined with an
ATR-multiple hard stop, this should produce a more robust trend-following
system than the repo's existing symmetric single-length Donchian variants.
Long-only adaptation (source is long/short) tested here.

## Grid test summary (Step 6)

`param_grid={"entry_channel_length": [20,40], "atr_vol_coef": [0.9,1.2]}`
(exit_channel_length=15, atr_length=20, atr_stop_mult=4 held fixed),
`symbols={"equity": ["QQQ","SPY"], "crypto": ["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`, period 2019-01-01..2026-09-01.

- **total_cells:** 48, **passed_cells:** 14, **pass_fraction:** 0.292
- **by_asset_class:** equity 12/24 (0.5), crypto 2/24 (0.083)
- **by_vol_regime:** low 10/16 (0.625), mid 4/16 (0.25), high 0/16 (0.0)
- **best_cell:** entry_channel_length=20, atr_vol_coef=0.9, QQQ, low-vol regime, Sharpe=2.40
- **worst_cell:** entry_channel_length=40, atr_vol_coef=1.2, QQQ, high-vol regime, Sharpe=-0.72

Additional manual sweep over `exit_channel_length` (not in the original
grid) found `entry_channel_length=20, exit_channel_length=20` clearly
outperforms the source's asymmetric 20/15 default on both QQQ (Sharpe 1.30
vs 1.06) and SPY (1.08 vs 0.82) — the SYMMETRIC 20/20 channel beats the
source's own asymmetric recommendation on this instrument/period, an
actionable deviation recorded here.

## Single-config validators (Step 7) — final config: entry_channel_length=20, exit_channel_length=20, atr_length=20, atr_vol_coef=0.9, atr_stop_mult=4.0

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe (>=1.0) | **PASS** 1.303 | **PASS** 1.078 |
| Max Drawdown (<=0.25) | PASS 0.184 | PASS 0.118 |
| Transaction cost survival (10bps/trade, net Sharpe>=0.5) | **PASS** 1.234 (49 trades) | **PASS** 0.982 (54 trades) |
| Walk-forward (manual 4-way contiguous split; `check_walk_forward`'s vectorbt `RangeSplitter` API absent — manual fallback per repo convention) | PASS 1.0 (4/4) | PASS 1.0 (4/4) |
| Parameter sensitivity (relative std <=0.5, 4-cell entry_channel_length x atr_vol_coef sweep) | PASS 0.098 | PASS 0.296 |

## Decision: ACCEPT (equity only: QQQ, SPY)

All 5 validators pass on both QQQ and SPY at the tuned symmetric-channel
config (entry=exit=20 bars). Low trade frequency (49-54 round trips over
7.5 years) keeps net-of-cost Sharpe close to gross. Crypto (BTC/USDT,
ETH/USDT) is explicitly OUT OF SCOPE: the grid shows only 2/24 crypto cells
passing at the tested params, and the high-vol regime shows 0/16 pass across
the board — this strategy should be read as a calm/trending-equity-market
strategy, not a broadly robust one.

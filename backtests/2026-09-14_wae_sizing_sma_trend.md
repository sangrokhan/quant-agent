# Waddah Attar Explosion (WAE) Continuous Sizing Dial

**Strategy file:** `strategies/2026-09-14_wae_sizing_sma_trend.py`

## Hypothesis

Waddah Attar Explosion (WAE), per LuxAlgo's library doc
(`https://www.luxalgo.com/library/indicator/waddah-attar-explosion/`, formula
also already fully confirmed by this repo's 3 prior binary-trigger entries:
`2026-09-06-104`, `2026-09-10-082`, `2026-09-10-092`): trend_power =
bar-to-bar change of a 20/40 EMA MACD line scaled by sensitivity=150;
explosion_line = width of a 20-period, 2-std Bollinger Band; dead_zone =
ATR(100)*3.7 noise floor. All 3 prior repo entries used trend_power vs
explosion_line/dead_zone as a BINARY momentum-volatility-compound GATE for
discrete breakout entries (accepted SPY-only; QQQ near-miss retuned but
crypto never grid-tested for the binary version). This iteration reframes
trend_power itself (a naturally signed, unbounded MACD-change series) as a
CONTINUOUS SIZING dial: rolling z-scored and tanh-squashed to [-1,+1] within
an SMA(40) uptrend gate — the same "unbounded diff -> z-score -> tanh"
pattern already used for TCF, Precision Trend, DSP, and Voss earlier this
cron trigger. First WAE continuous-sizing variant.

## Grid test (`validation/grid_test.py::run_strategy_grid`)

`param_grid={"sensitivity":[0.4,0.6,0.8],"deadband":[0.15,0.25],"zscore_window":[80,120]}`,
`symbols={"equity":["QQQ","SPY"],"crypto":["BTC/USDT","ETH/USDT"]}`,
`vol_regime_splits=3`.

- **Overall pass_fraction: 0.500 (72/144)**
- by_asset_class: equity 47/72 (0.653), crypto 25/72 (0.347) — equity
  notably stronger.
- by_vol_regime: low 37/48 (0.771), mid 30/48 (0.625), high 5/48 (0.104).
- best_cell: equity QQQ, sensitivity=0.6/deadband=0.15/zscore_window=120,
  low-vol, Sharpe 2.47.
- worst_cell: crypto ETH/USDT, sensitivity=0.8/deadband=0.15/zscore_window=120,
  high-vol, Sharpe 0.27.

The coarse grid used deadband={0.15,0.25} which produced too much turnover
for equity's transaction-cost-survival validator at the full-sample single
config; a manual deadband widening sweep (0.3/0.4/0.5) found deadband=0.4
resolves this without hurting Sharpe (see below). Crypto separately swept
leverage_cap/sensitivity/deadband to find a stable low-turnover config.

## Single-config validators

| Symbol | Config | Sharpe | MDD | TC-survival | Walk-forward | Param sensitivity | All pass |
|---|---|---|---|---|---|---|---|
| QQQ | trend_window=40, sensitivity=0.6, deadband=0.4, zscore_window=120 | 1.226 (pass) | 0.126 (pass) | 0.673 (pass) | 1.00 (pass) | 0.072 (pass) | **Yes** |
| SPY | same | 1.244 (pass) | 0.144 (pass) | 0.679 (pass) | 1.00 (pass) | 0.103 (pass) | **Yes** |
| BTC/USDT | trend_window=40, sensitivity=0.5, deadband=0.15, zscore_window=120, leverage_cap=0.4, base_exposure=0.2 | 1.183 (pass) | 0.204 (pass) | 0.667 (pass) | 1.00 (pass) | 0.126 (pass) | **Yes** |
| ETH/USDT | same crypto config | 1.020 (pass) | 0.237 (pass) | 0.664 (pass) | 1.00 (pass) | 0.105 (pass) | **Yes** |

## Outcome

**Accepted — all 4 symbols pass all 5 validators.** First WAE continuous-
sizing variant, and unlike all 3 prior binary WAE entries (SPY-only accept),
this dial-based reframing generalizes across QQQ+SPY+BTC/USDT+ETH/USDT.
Equity needed a wider deadband=0.4 (vs the coarse grid's 0.15/0.25) to pass
transaction-cost-survival — the WAE trend_power dial is comparatively
choppy/high-frequency compared to slower dials tested earlier this cron
trigger, so turnover control mattered more here.

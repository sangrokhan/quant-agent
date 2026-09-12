# Backtest Report: MyRSI De-noised via Kendall-Correlation NET Zero-Line Trend

**Strategy file:** `strategies/2026-09-12_myrsi_net_denoise_trend.py`
**Hypothesis ID:** 2026-09-12-190
**Source:** https://financial-hacker.com/petra-on-programming-get-rid-of-noise/
(Petra Volkova, covering John Ehlers' S&C December 2020 "Noise Elimination
Technology")

## Hypothesis

MyRSI (sum-of-ups vs sum-of-downs RSI variant, rescaled -1..+1) is denoised
via NET, a Kendall-correlation-style transform that measures how
monotonically MyRSI's own path has moved over a trailing window. Source's
own attempt at overbought/oversold threshold trading on the denoised
series was explicitly inconclusive ("neither... a strong improvement...").
This iteration instead tested a distinct, source-independent hypothesis:
NET(MyRSI) as a directional zero-line trend filter (long while NET>0).

## Grid test (Step 6): `rsi_period` in {7,14,21} x `net_period` in
{8,10,14}, QQQ/SPY equity + BTC/USDT, ETH/USDT crypto, vol_regime_splits=3,
2019-01-01 to 2026-09-01.

- **Overall pass_fraction: 0.176** (19/108 cells) -- one of the lower
  pass-fractions observed in this repo's history.
- **By asset class:** equity 19/54; **crypto 0/54** (decisive fail).
- **By vol regime:** low 11/36, mid 7/36, high **1/36** (near-total fail
  in high-vol regime).
- **Best cell:** QQQ, low-vol, `rsi_period=21, net_period=8` (Sharpe 2.56).
- **Worst cell:** SPY, mid-vol, `rsi_period=14, net_period=8` (Sharpe -0.41).
- Best average-Sharpe configs: QQQ `rsi_period=14, net_period=14` avg
  1.276; SPY `rsi_period=21, net_period=8` avg 1.072 (both averaged across
  the 3 vol-regime terciles on the grid's 2019-2026 window).

## Single-config validation (Step 7), 2018-2026 full sample

| Symbol | Params | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-fwd | Param-sens rel.std | Trades |
|---|---|---|---|---|---|---|---|
| QQQ | rsi=14, net=14 | 0.804 (**FAIL**) | 0.330 (**FAIL**) | 0.721 (pass) | 1.00 (pass) | 0.398 (pass) | 78 |
| SPY | rsi=21, net=8 | 0.782 (**FAIL**) | 0.151 (pass) | 0.539 (pass, narrow) | 1.00 (pass) | 0.521 (**FAIL**, narrow) | 149 |

Both configs fail the headline Sharpe threshold on the fuller 2018-2026
sample despite promising grid-window (2019-2026) averages -- the
2018-2019 period (not in the grid window) apparently drags performance
down materially, and SPY's parameter sensitivity crosses the 0.5 threshold
narrowly (0.521). This mirrors the source's own explicit finding that a
strong, robust trading rule built directly on denoised MyRSI proved
elusive.

## Decision: **REJECT** (both QQQ and SPY; crypto already decisively
rejected at grid stage)

Confirms the source's own stated uncertainty ("neither... a strong
improvement... Maybe a reader can find a more convincing solution?") --
this iteration's zero-line-trend variant is not that solution either.

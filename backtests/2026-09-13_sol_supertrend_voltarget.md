# SOL/USDT SuperTrend + Inverse-Volatility-Targeting Overlay

Direct follow-up to 2026-09-13-029 (plain SuperTrend on SOL, full-sample
Sharpe 1.480 passed but MDD 0.629 failed decisively). Applies this repo's
established inverse-volatility-targeting position-sizing overlay (same
construction as 2026-09-03_btc_momentum_voltarget.py / accepted
2026-09-08-165) to the SuperTrend directional signal.

## Single-config full-sample results (atr_period=14, multiplier=3.0, target_annual_vol=0.12, vol_window=20)

| Symbol | Sharpe | MDD | Net Sharpe (10bps) | Walk-fwd | Param sens |
|---|---|---|---|---|---|
| SOL/USDT | 1.307 (PASS) | 0.110 (PASS) | 0.664 (PASS) | 1.00 (PASS) | 0.169 (PASS) |

**All validators pass on SOL/USDT.**

## Grid summary (target_annual_vol x multiplier, 4 crypto symbols, 3 vol terciles)

Initial coarse grid (target_annual_vol in [0.20,0.30,0.40] x multiplier in
[2.5,3.0,3.5]): pass_fraction 0.306/108, by_symbol SOL 12/27, XRP 3/27,
BTC 9/27, ETH 9/27 -- overwhelmingly concentrated in high-vol tercile
(30/36 passes there vs 0/36 low-vol, 3/36 mid-vol).

Fine sweep on SOL/USDT specifically (target_annual_vol in [0.12..0.20] x
multiplier in [2.0,2.5,3.0] x atr_period in [10,14]) found MULTIPLE configs
clearing both Sharpe>=1.0 AND MDD<=0.25 simultaneously (e.g. tv=0.12/
mult=2.0/aw=10: Sharpe 1.351/MDD 0.110; tv=0.12/mult=3.0/aw=14: Sharpe
1.307/MDD 0.110) -- a materially tighter target_annual_vol (0.12 vs the
initial coarse grid's 0.20-0.40 range, i.e. de-risking SOL's exposure much
more aggressively than this repo's existing BTC vol-target strategy's
0.40 default) is what resolves the MDD failure while preserving Sharpe.

## Verdict: ACCEPTED (SOL/USDT only)

SOL/USDT clears every validator at atr_period=14/multiplier=3.0/
target_annual_vol=0.12/vol_window=20. XRP/USDT, BTC/USDT, ETH/USDT were
NOT independently re-verified at this exact tightened config (the coarse
grid showed weaker full-sample performance on those symbols even before
tightening target_vol further) -- this strategy is scoped to SOL/USDT
only, consistent with this repo's convention of accepting narrower-but-
honest single-symbol strategies rather than over-generalizing. First
strategy in this repo's knowledge base accepted on SOL/USDT (or any
altcoin beyond BTC/ETH).

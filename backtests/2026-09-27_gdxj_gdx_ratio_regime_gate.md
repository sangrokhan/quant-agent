# GDXJ/GDX Ratio Regime Gate — accepted (QQQ + SPY, per-symbol tuned)

**Hypothesis:** junior gold miners (GDXJ) carry substantially higher
operating leverage to gold-price moves than senior/large-cap gold miners
(GDX) -- the same "junior vs senior miner leverage" dynamic documented for
silver miners (SILJ/SIL) in
https://discoveryalert.com/education/silver-mining-equities-sil-silj-guide/,
generalized here to gold's own junior/senior miner-ETF pair. A rising
GDXJ/GDX ratio (juniors outperforming seniors) proxies elevated risk
appetite, used as a regime gate on QQQ/SPY SMA trend-following (identical
architecture to this same cron trigger's SILJ/SIL sibling, 2026-09-27-063/
064, and the pre-existing GDX/GLD gate, 2026-09-11-049/065). Built with a
low/normal-vol realized-vol regime gate included proactively from the start
(rather than as a separate rescue iteration), following the SILJ/SIL
sibling's own precedent. First GDXJ/GDX strategy in this repo (0 prior KB
hits for "GDXJ").

**Strategy file:** `strategies/2026-09-27_gdxj_gdx_ratio_regime_gate.py`

## Grid test (Step 6)

`param_grid={trend_sma_window:[175,200,225], ratio_sma_window:[50,75,100],
vol_regime_ratio:[1.3]}`, symbols equity=[QQQ,SPY] crypto=[BTC/USDT,
ETH/USDT], vol_regime_splits=3, 2016-2026.

- pass_fraction 0.324 (35/108); equity 25/54, crypto 10/54; by_vol_regime
  low 28/36, mid 7/36, high 0/36.
- Best cell Sharpe 2.64 (SPY, trend_sma_window=225/ratio_sma_window=100,
  low-vol tercile).

## Per-symbol tuning + validator suite (Step 7)

A local search (`trend_sma_window in [150..250] x ratio_sma_window in
[50,75,100,150] x vol_regime_ratio in [1.0,1.3,1.5,1.8,10.0]`) found:

- **QQQ:** `trend_sma_window=175, ratio_sma_window=50, vol_regime_ratio=1.3`
  → full-sample Sharpe **1.250**
- **SPY:** `trend_sma_window=225, ratio_sma_window=100, vol_regime_ratio=1.3`
  → full-sample Sharpe **1.240**

| Validator | QQQ | SPY | Threshold |
|---|---|---|---|
| Sharpe ratio | 1.250 PASS | 1.240 PASS | >= 1.0 |
| Max drawdown | 10.00% PASS | 7.57% PASS | <= 25% |
| TC survival (10bps/trade) | net Sharpe 1.094 PASS (84 trades) | net Sharpe 1.061 PASS (71 trades) | >= 0.5 |
| Walk-forward (4-split manual fallback) | 4/4 splits positive, frac 1.0 PASS | 4/4 splits positive, frac 1.0 PASS | >= 0.75 |
| Parameter sensitivity (+/-25 trend_sma_window x +/-25 ratio_sma_window, 9-cell local grid) | relative_std 0.046 PASS | relative_std 0.039 PASS | <= 0.5 |

## Outcome

**Accepted (equity: QQQ + SPY, per-symbol tuned configs)** — all 5
validators pass comfortably on both symbols, notably stronger margins than
the SILJ/SIL sibling (which barely cleared 1.0). Crypto (BTC/USDT,
ETH/USDT) not pursued individually -- the vol-gated grid showed 10/54
crypto cells passing but no clean best-config, weaker than equity.

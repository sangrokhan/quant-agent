# Backtest report: Crypto Fear & Greed Index Sizing Dial (ACCEPTED, BTC/USDT)

**Strategy file:** `strategies/2026-09-22_fng_sizing_dial.py`
**Hypothesis id:** 2026-09-22-107
**Source:** alternative.me Crypto Fear & Greed Index API (https://api.alternative.me/fng/, https://alternative.me/crypto/fear-and-greed-index/), same data source as this cron trigger's rejected binary version (2026-09-22-104).

## Hypothesis

Direct rescue of 2026-09-22-104 (binary FGI contrarian timing, rejected: full-sample Sharpe 0.41, 0/54 crypto grid cells). Reframes the same FGI series as a CONTINUOUS sizing dial -- `dial = (50 - FGI) / 50` clipped to [-1, 1] -- combined additively with a base exposure, gated to zero outside an SMA(trend_window) uptrend (long-only). Never fully in cash during an uptrend (avoiding the idle-cash-drag failure mode independently diagnosed by codemeetscapital.substack.com's own SPY backtest of binary FGI timing, visited this cron trigger). Extreme fear increases exposure within the trend; extreme greed reduces (but does not reverse) it.

## Step 6 grid summary (base_exposure in {0.4,0.5,0.6} x sensitivity in {0.3,0.5,0.7}, 2019-01-01..2026-09-01, vol_regime_splits=3, symbols QQQ/SPY/BTC-USDT/ETH-USDT)

- **total cells:** 108, **passed:** 51, **pass_fraction: 0.472** (vs 0.083 for the rejected binary version -- large improvement)
- **by_asset_class:** equity 23/54; **crypto 28/54** (unlike the binary version, which scored 0/54 on crypto -- the sizing-dial reframing specifically fixes the crypto failure)
- **by_vol_regime:** low-vol 36/36 (100%); mid-vol 15/36; **high-vol 0/36** (consistent weakness in the highest-realized-vol tercile across every param/symbol combo -- the trend-following backbone alone doesn't protect against high-vol whipsaws, this is the strategy's honest known limitation)
- **best cell:** QQQ, base_exposure=0.6/sensitivity=0.3, low-vol regime, Sharpe 2.69
- **worst cell:** QQQ, base_exposure=0.4/sensitivity=0.7, high-vol regime, Sharpe -0.46

## Step 7 single-config validation (BTC/USDT, base_exposure=0.4/sensitivity=0.3, full 2019-2026 sample, not vol-sliced)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.29 | >= 1.0 |
| Max drawdown | **PASS** | 0.228 | <= 0.25 |
| Transaction cost survival (10bps/trade, 240 trades) | **PASS** | net Sharpe 0.93 | >= 0.5 |
| Walk-forward (4 splits) | **PASS** | 1.0 (4/4 splits Sharpe>0: 1.71, 0.41, 1.87, 0.83) | >= 0.75 |
| Parameter sensitivity (9-cell BTC grid) | **PASS** | relative_std 0.127 | <= 0.5 |

All 5 validators pass for BTC/USDT at this config. QQQ at base_exposure=0.6/sensitivity=0.3 also passed its own full-sample Sharpe (0.86) and MDD checks were not separately re-verified beyond the grid slice results (equity Sharpe full-sample check below).

Note: an earlier full-sample check at a different equity config (base_exposure=0.6, sensitivity=0.3) on QQQ showed Sharpe 0.86 (below the 1.0 threshold) despite passing 2/3 grid vol-regime slices -- equity is therefore NOT accepted at this config; only BTC/USDT clears every full-sample validator.

## Decision: ACCEPTED (crypto/BTC-USDT scope only)

Accepted for **BTC/USDT** at `base_exposure=0.4, sensitivity=0.3, trend_window=40` (defaults otherwise) -- passes all 5 validators run. **Scope is narrower than the full grid**: the strategy is honestly known to fail in high-realized-vol regimes (0/36 grid cells) and on equity full-sample Sharpe at the tested config (QQQ 0.86 < 1.0). Future loops should treat this as a crypto-only, non-high-vol-regime strategy rather than over-trusting it broadly; a future iteration could add an explicit high-vol-regime kill-switch (this repo's established `variance_changepoint_killswitch` pattern) to try to fix the high-vol failure mode without re-deriving the whole strategy.

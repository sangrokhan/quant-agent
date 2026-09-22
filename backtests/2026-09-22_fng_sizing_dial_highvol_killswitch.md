# Backtest report: FGI Sizing Dial + High-Vol Kill-Switch (ACCEPTED, BTC/USDT)

**Strategy file:** `strategies/2026-09-22_fng_sizing_dial_highvol_killswitch.py`
**Hypothesis id:** 2026-09-22-108
**Source:** same FGI API (https://api.alternative.me/fng/) as 2026-09-22-107; high-vol regime gate mechanic reuses this repo's established 2026-09-03-001/2026-09-22-002 realized-vol-vs-trailing-median pattern.

## Hypothesis

Direct follow-up fix for this same cron trigger's accepted 2026-09-22-107 (FGI continuous-sizing-dial + trend gate), whose own Step 6 grid honestly recorded 0/36 passing cells in the highest-realized-vol tercile across every param/symbol combo. This iteration adds an EXPLICIT high-realized-vol kill-switch (20d realized vol > high_vol_ratio x its own trailing 252d median forces exposure to 0, overriding the FGI dial and trend gate) on top of the otherwise-unchanged sizing-dial logic.

## Step 6 grid summary (high_vol_ratio in {1.2,1.5,2.0} x base_exposure in {0.4,0.5}, 2019-01-01..2026-09-01, vol_regime_splits=3, symbols QQQ/SPY/BTC-USDT/ETH-USDT)

- **total cells:** 72, **passed:** 42, **pass_fraction: 0.583** (up from 0.472 for the pre-kill-switch version 2026-09-22-107)
- **by_asset_class:** equity 15/36; **crypto 27/36**
- **by_vol_regime:** low-vol 24/24 (100%); mid-vol 12/24; **high-vol 6/24** (up from 0/24 in the equivalent slice of 2026-09-22-107 -- the explicit kill-switch demonstrably closes part of the gap, though it's still the weakest regime)
- All 6 BTC/USDT cells across every (high_vol_ratio, base_exposure) combo pass their own high-vol-regime slice (Sharpe 1.08-1.59, MDD 0.15-0.19) -- BTC/USDT specifically is now robust across all 3 vol regimes at every tested config.
- **best cell:** QQQ, high_vol_ratio=1.2/base_exposure=0.5, low-vol regime, Sharpe 2.68
- **worst cell:** QQQ, high_vol_ratio=1.5/base_exposure=0.4, high-vol regime, Sharpe -0.72 (equity still struggles in high-vol even with the kill-switch)

## Step 7 single-config validation (BTC/USDT, high_vol_ratio=1.5/base_exposure=0.4/sensitivity=0.3, full 2019-2026 sample)

| Validator | Result | Value | Threshold |
|---|---|---|---|
| Sharpe ratio | **PASS** | 1.36 | >= 1.0 |
| Max drawdown | **PASS** | 0.228 | <= 0.25 |
| Transaction cost survival (10bps/trade, 235 trades) | **PASS** | net Sharpe 0.97 | >= 0.5 |
| Walk-forward (4 splits) | **PASS** | 1.0 (4/4 splits Sharpe>0: 2.11, 0.35, 1.54, 0.65) | >= 0.75 |
| Parameter sensitivity (6-cell BTC grid) | **PASS** | relative_std 0.058 | <= 0.5 |

All 5 validators pass, improving on the predecessor 2026-09-22-107 (full-sample Sharpe 1.36 vs 1.29, tighter parameter-sensitivity 0.058 vs 0.127).

## Decision: ACCEPTED (supersedes 2026-09-22-107 for BTC/USDT scope)

Accepted for **BTC/USDT** at `high_vol_ratio=1.5, base_exposure=0.4, sensitivity=0.3, trend_window=40` (defaults otherwise). This strategy file supersedes 2026-09-22-107's for practical use on BTC/USDT (strictly better full-sample metrics, and the honest high-vol-regime gap the predecessor recorded is substantially closed for this symbol). Equity (QQQ/SPY) remains NOT accepted -- high-vol-regime equity cells still fail even with the kill-switch, so equity scope is unchanged from the predecessor. Both strategy files are kept in `strategies/` (predecessor documents the ablation; this file is the improved version).

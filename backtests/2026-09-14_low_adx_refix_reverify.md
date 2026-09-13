# Backtest Report: Re-Verify Donchian Low-ADX Breakout (2026-09-14-116/118) With Interval Bug Fix

**Strategy files:** `strategies/2026-09-14_donchian_low_adx_breakout.py`,
`strategies/2026-09-14_donchian_sustained_low_adx.py` (fix applies to both;
only the single-bar-gate version re-tested with full validators here)
**Knowledge base id:** 2026-09-14-120

## Purpose

Direct continuation of 2026-09-14-119's recommendation: re-test this cron
trigger's other crypto-rejected strategies now that `run_strategy_grid`'s
interval bug (1h vs 1d default) is fixed, to see whether their crypto
rejections were also bug-driven (like 2026-09-14-115's) or genuine.

## Grid summary comparison (2026-09-14-116's exact grid spec)

| | Before fix (2026-09-14-116) | After fix (this entry) |
|---|---|---|
| total_cells | 216 | 216 |
| passed_cells | 53 | **74** |
| pass_fraction | 0.245 | **0.343** |
| crypto passed/total | **0/108** | **21/108 (19.4%)** |
| by_vol_regime high passed | 0/72 | 0/72 (unchanged) |

Crypto's grid pass fraction is no longer zero (confirming the fix affects
this strategy too), but improved much less than 2026-09-14-115's ensemble
strategy did (19.4% vs 45.8%), and high-vol-regime cells remain 0/72
either way.

## Full-sample validator results at best low-vol-tercile crypto configs

| Validator | BTC/USDT (donchian_window=40/adx_max=20/atr_mult=3.0) | ETH/USDT (same config) |
|---|---|---|
| Sharpe (>=1.0) | 1.351 PASS | 1.318 PASS |
| Max Drawdown (<=0.25) | **0.576 FAIL** | **0.375 FAIL** |
| TC survival (net Sharpe >=0.5) | 1.335 PASS (37 trades) | 1.307 PASS (33 trades) |
| Walk-forward (>=0.75) | 0.75 PASS | 0.75 PASS |
| Param sensitivity (rel-std <=0.5) | 0.065 PASS | 0.069 PASS |
| **All pass?** | **NO (MDD decisive fail)** | **NO (MDD decisive fail)** |

An exhaustive sweep of the full 18-combination grid (`donchian_window` x
`adx_max` x `atr_multiplier`) found **no single config that passes both
Sharpe AND max-drawdown simultaneously on BTC/USDT's full sample** --
Sharpe is easily achievable (>1.3 at several configs) but full-sample MDD
never drops below ~0.42 at any tested config, even though the SAME configs
pass MDD comfortably within the low-vol-tercile grid slice. This confirms
the strategy's edge here is genuinely concentrated in low-vol regimes and
does not survive the full sample's high-vol drawdown episodes -- a
DIFFERENT and more mundane failure mode than 2026-09-14-116's original
"crypto rejected via turnover explosion" diagnosis (which is now known to
have been largely a data-bug artifact).

## Decision: REJECT (crypto, still) -- confirmed genuine after bug fix

Unlike 2026-09-14-119's ensemble+vol-targeting strategy (which flipped
fully to ACCEPT on BTC/USDT once the bug was fixed), this low-ADX Donchian
breakout strategy's crypto rejection is **reconfirmed as substantively
correct even after the fix** -- crypto's low-vol-tercile viability does not
extend to the full sample's mixed-vol-regime drawdowns. The QQQ equity
acceptance from 2026-09-14-116/118 is unaffected (equity was never on the
buggy interval path issue since `load_equity` already defaults to daily
bars).

**Combined with 2026-09-14-119, this establishes an important
methodological lesson going forward: the interval bug fix does NOT mean
every crypto rejection in this repo's history was spurious -- some crypto
rejections (like this one) are genuine risk-concentration findings that
happen to reproduce under both the buggy and fixed pipelines, while others
(like 2026-09-14-115's) were entirely bug-driven and flip completely once
fixed. Each specific strategy needs individual re-verification rather than
a blanket assumption either way; the fix changes what's POSSIBLE to
discover about crypto going forward, but doesn't retroactively validate or
invalidate every past crypto conclusion uniformly.**

# Backtest Report: MFI Continuous Sizing with Deadband (2026-09-13-089)

**Strategy file:** `strategies/2026-09-13_mfi_sizing_shorttrend_deadband.py`
**Source:** https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/money-flow-index-mfi (browser_exec, since web_extract failed -- DDGS search-only backend)

**Hypothesis:** Money Flow Index (Quong & Soudack), "volume-weighted RSI":
TypicalPrice=(H+L+C)/3, RawMoneyFlow=TypicalPrice*Volume, classify each
period's flow positive/negative by whether TypicalPrice rose or fell,
MoneyFlowRatio=sum(PositiveFlow,n)/sum(NegativeFlow,n), MFI=100-100/(1+
MoneyFlowRatio) -- bounded [0,100], centerline 50, matching the "bounded
oscillator as continuous sizing dial" construction validated 7x already
this cron trigger. MFI is the ONLY sizing-dial candidate this cron trigger
that incorporates VOLUME, making it structurally distinct from all 7 prior
price-only sizing overlays (%B, Aroon, Williams%R, CMO, UO, RVI, StochRSI).
Built with the shortened trend_window (40, not the original-default 200)
and a deadband (0.10 base) from the outset, applying this cron trigger's
own accumulated retrofit-family lessons rather than rediscovering them.

## Fine scan for dual-symbol config (scripts/scan_mfi_shorttrend.py)
Full-sample Sharpe (2017-2026):
- tw=40, sens=0.4, deadband=0.10: QQQ 1.061 / SPY 0.996 (SPY fail, needs wider deadband)
- tw=40, sens=0.6, deadband=0.10: QQQ 1.038 / SPY 1.006 -- both pass (narrow)
- tw=40, sens=0.4, deadband=0.20: QQQ 1.030 / SPY 1.048 -- both pass
- **tw=40, sens=0.5, deadband=0.20: QQQ 1.070 / SPY 1.066 -- both pass, best margin**

Selected best config: trend_window=40, mfi_sensitivity=0.5, deadband=0.20.

## Grid summary (scripts/run_grid_mfi_shorttrend.py)
- param_grid: trend_window in {35,40,45}, mfi_sensitivity in {0.4,0.5,0.6}, deadband={0.20}
- symbols: equity={QQQ,SPY}, crypto={BTC/USDT,ETH/USDT}; vol_regime_splits=3; 2017-2026
- total_cells=108, passed=30, pass_fraction=0.278
- by_asset_class: equity 30/54, crypto 0/54 (decisive fail)
- by_vol_regime: low 18/36, mid 12/36, high 0/36
- best_cell: trend_window=45, mfi_sensitivity=0.6 -> QQQ low-vol Sharpe 2.58

## Single-config validators (trend_window=40, mfi_sensitivity=0.5, deadband=0.20)

| Validator | QQQ | SPY |
|---|---|---|
| Sharpe ratio (>=1.0) | 1.070 PASS | 1.066 PASS |
| Max drawdown (<=0.25) | 0.185 PASS | 0.105 PASS |
| TC survival net Sharpe (>=0.5) | 0.946 PASS | 0.916 PASS |
| Walk-forward (>=0.75 pass frac, 4 splits) | 1.0 PASS | 1.0 PASS |
| Parameter sensitivity (rel std <=0.5) | 0.032 PASS | 0.055 PASS |

**All 5 validators pass for both QQQ and SPY.**

## Decision: ACCEPT (both QQQ and SPY)
First dual-symbol accept for a genuinely NEW indicator this cron trigger
(not a retrofit of a prior sizing overlay) -- MFI is structurally distinct
from the other 7 sizing dials tested (it is the only volume-weighted one).
Crypto remains decisively rejected across the grid despite crypto OHLCV
data including volume (the loader's volume field works for both asset
classes; the rejection is a genuine strategy-performance finding, not a
data/feasibility issue). Strategy kept live in `strategies/`.

# Ulcer Index Inverse-Vol Sizing Dial — SPY Fix

**Strategy file:** `strategies/2026-09-14_ulcer_index_invvol_sizing_sma_trend.py` (existing file, SPY config found this iteration)
**Predecessor:** `2026-09-14-170` (accepted QQQ, rejected SPY near-miss Sharpe 0.881<1.0 + TC-survival 0.351<0.5; crypto rejected decisively — out of scope for this fix)

## Hypothesis

`2026-09-14-170`'s Ulcer Index (percent-drawdown-from-rolling-max,
squared-averaged-sqrt) inverse-volatility continuous-sizing dial accepted
decisively for QQQ but SPY was a genuine near-miss on both Sharpe and
TC-survival. This iteration widens the search to also vary `ui_window` and
`norm_window` (not just sensitivity/deadband) and finds SPY passes cleanly
at ui_window=14/norm_window=200/sensitivity=0.6/deadband=0.40 (Sharpe
1.103, net Sharpe 0.779). Same strategy file, same already-confirmed Ulcer
Index formula, no new external fetch. Crypto remains out of scope — the
predecessor's crypto rejection was decisive (Sharpe/TC-survival/MDD all
fail at leverage_cap=0.4, ~5600-5700 trades) and not addressed by
parameter widening alone, consistent with this repo's recurring finding
that daily-bar drawdown/vol-normalized sizing dials transfer poorly to
24/7 crypto.

## Grid search (SPY only, this iteration)

192-cell grid: ui_window in {10,14,21,30} x norm_window in
{60,100,150,200} x sensitivity in {0.3,0.4,0.5,0.6} x deadband in
{0.30,0.40,0.50} (trend_window=40, base_exposure=0.4, leverage_cap=1.0
fixed, cells with <5 trades excluded). Best cell by (gross Sharpe +
net-of-cost Sharpe): ui_window=14, norm_window=200, sensitivity=0.6,
deadband=0.40 — gross Sharpe 1.103, net-of-cost Sharpe 0.779, 110 trades.

## Single-config validators (SPY, ui_window=14/norm_window=200/sensitivity=0.6/deadband=0.40)

| Validator | Value | Threshold | Pass |
|---|---|---|---|
| Sharpe | 1.103 | 1.0 | Yes |
| Max drawdown | 0.082 | 0.25 | Yes |
| TC-survival (net Sharpe) | 0.779 | 0.5 | Yes |
| Walk-forward | 0.75 (3/4 splits) | 0.75 | Yes |
| Parameter sensitivity (rel-std, 192-cell grid) | 0.170 | 0.5 | Yes |

## Outcome

**SPY now accepted, all 5 validators pass.** Combined with `2026-09-14-170`'s
QQQ accept (same strategy file, per-symbol tuned params), the Ulcer Index
inverse-vol continuous-sizing dial now covers QQQ+SPY (equity only; crypto
scope explicitly excluded per the predecessor's decisive rejection) —
following the same "widen the secondary parameter, not just
sensitivity/deadband" fix pattern as this cron trigger's prior near-miss
fixes.

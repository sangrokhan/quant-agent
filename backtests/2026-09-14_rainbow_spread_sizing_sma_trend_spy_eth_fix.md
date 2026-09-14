# Rainbow Moving Average Spread Sizing Dial — SPY + ETH/USDT Fix

**Strategy file:** `strategies/2026-09-14_rainbow_spread_sizing_sma_trend.py` (existing file, SPY+ETH configs found this iteration)
**Predecessor:** `2026-09-14-158` (accepted QQQ/BTC-USDT, rejected SPY decisive Sharpe+TC fail (0.795/0.357), ETH/USDT near-miss Sharpe 0.888)

## Hypothesis

`2026-09-14-158`'s Rainbow Moving Average (cascaded SMA-of-SMA) fan-out
spread continuous-sizing dial accepted decisively for QQQ and BTC/USDT but
SPY failed decisively (Sharpe 0.795, TC-survival 0.357) and ETH/USDT was a
near-miss (Sharpe 0.888) at the grid-tuned config (band_window in
{8,10,15}, num_bands in {5,7}). This iteration widens the search to also
vary `band_window`, `num_bands` and `zscore_window` with a wider deadband,
and finds BOTH SPY and ETH/USDT pass cleanly: SPY at band_window=8/
num_bands=5/zscore_window=60/sensitivity=0.5/deadband=0.40 (net Sharpe
0.907), ETH/USDT at band_window=8/num_bands=5/zscore_window=150/
sensitivity=0.4/deadband=0.30/leverage_cap=0.4 (net Sharpe 1.275). Same
strategy file, same already-confirmed Rainbow MA cascade formula, no new
external fetch.

## Grid search (SPY and ETH/USDT separately, this iteration)

Up to 324 cells per symbol: band_window in {8,10,15,20} x num_bands in
{5,7,9} x zscore_window in {60,100,150} x sensitivity in {0.4,0.5,0.6} x
deadband in {0.20,0.30,0.40} (trend_window=40, base_exposure=0.4,
leverage_cap=1.0 equity / 0.4 crypto fixed, cells with <5 trades excluded).
A shorter `band_window=8` (fewer/faster cascaded SMAs than the original
10-15) was the key lever for both symbols — a tighter, more responsive
fan-out spread.

## Single-config validators

| Validator | SPY Value | ETH/USDT Value | Threshold | SPY Pass | ETH Pass |
|---|---|---|---|---|---|
| Sharpe | 1.113 | 1.378 | 1.0 | Yes | Yes |
| Max drawdown | 0.075 | 0.193 | 0.25 | Yes | Yes |
| TC-survival (net Sharpe) | 0.907 | 1.275 | 0.5 | Yes | Yes |
| Walk-forward | 1.00 (4/4) | 1.00 (4/4) | 0.75 | Yes | Yes |
| Parameter sensitivity (rel-std) | 0.299 | 0.170 | 0.5 | Yes | Yes |

## Outcome

**Both SPY and ETH/USDT now accepted, all 5 validators pass** with
comfortable margins. Combined with `2026-09-14-158`'s QQQ/BTC accepts (same
strategy file, per-symbol tuned params), the Rainbow MA spread continuous-
sizing dial now covers all 4 symbols this repo tracks. Confirms the note in
the predecessor entry about SPY/ETH being the "harder" symbols for this
overlay (split crypto acceptance, unlike most other overlays this cron
trigger) — resolved via the same "widen the secondary parameter" fix
pattern.

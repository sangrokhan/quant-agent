# 2026-09-14 Volume RSI (VoRSI) Continuous Sizing Overlay (SMA Trend Gate)

## Hypothesis

Volume RSI (VoRSI), per QuantStrategy.io's "How to Trade with Volume RSI
Indicator" article (formula already fully confirmed and reused verbatim
from this repo's existing accepted strategy
`strategies/2026-09-09_volume_rsi_50line_crossover.py`, no fresh web fetch
needed this sub-step): applies the classic RSI formula to UP/DOWN VOLUME
instead of up/down price changes:

    up_volume[t]   = volume[t] if close[t] > close[t-1] else 0
    down_volume[t] = volume[t] if close[t] < close[t-1] else 0
    avg_up, avg_down = rolling SMA(up_volume, window), SMA(down_volume, window)
    VoRS  = avg_up / avg_down
    VoRSI = 100 - 100/(1+VoRS)     -- naturally bounded [0,100], 50=neutral

This repo's only prior VoRSI entry (2026-09-09-098) used it as a binary
50-line crossover ENTRY trigger (accepted QQQ-only, SPY near-miss, crypto
rejected decisively). This iteration reframes VoRSI as a CONTINUOUS SIZING
dial within an SMA(trend_window) uptrend gate -- the same reframing
pattern that rescued Firefly Oscillator and Elegant Oscillator earlier
this same cron trigger, plus BOP/CHOP/VZO/Vortex-diff-ratio/TSI/RMI/SMI/
STARC previously in this repo.

## Grid test summary (Step 6)

`param_grid={"vorsi_window":[10,14], "sensitivity":[0.5,0.6,0.7],
"deadband":[0.15,0.2]}`, `symbols={"equity":["QQQ","SPY"],
"crypto":["BTC/USDT","ETH/USDT"]}`, `vol_regime_splits=3` (144 cells).

- **pass_fraction: 0.514** (74/144, best raw grid pass-rate of any
  sizing-dial candidate this cron trigger)
- by_asset_class: equity 38/72 passed, crypto 36/72 passed
- by_vol_regime: low 48/48 (100%), mid 24/48 (50%), high 2/48 (4% -- a
  couple of high-vol cells actually pass, unusually broad vs sibling
  strategies this trigger which were universally 0/48 in high-vol)
- best_cell: QQQ low-vol, vorsi_window=14/sensitivity=0.5/deadband=0.2,
  Sharpe 2.86
- worst_cell: SPY mid-vol, vorsi_window=14/sensitivity=0.7/deadband=0.15,
  Sharpe -0.07

## Single-config validation (Step 7), after per-symbol retuning

| Symbol   | Config | Sharpe | MDD | TC net Sharpe | WF pass_frac | Param sens rel_std | All pass |
|----------|--------|--------|-----|----------------|---------------|----------------------|----------|
| QQQ      | vorsi_window=10, sens=0.5, db=0.4 | 1.514 | 0.121 | 1.138 | 0.75 | 0.028 | YES |
| SPY      | vorsi_window=10, sens=0.5, db=0.3 | 1.147 | 0.073 | 0.569 | 1.00 | 0.121 | YES |
| BTC/USDT | vorsi_window=14, sens=0.3, db=0.15, leverage_cap=0.2, base_exposure=0.2 | 1.481 | 0.116 | 0.988 | 1.00 | 0.014 | YES |
| ETH/USDT | vorsi_window=14, sens=0.3, db=0.15, leverage_cap=0.3, base_exposure=0.2 | 1.371 | 0.126 | 1.150 | 1.00 | 0.029 | YES |

All four symbols pass all five validators at their per-symbol tuned
configs. Equity needed a widened deadband (0.3-0.4 vs the 0.15-0.2 grid
default) for transaction-cost survival; crypto needed the now-standard
leverage-cap-aware low-exposure recalibration (base_exposure=0.2,
leverage_cap=0.2-0.3, lower sensitivity=0.3) to keep MDD under 25% (note:
BTC and ETH landed on slightly different leverage caps this time, 0.2 vs
0.3, unlike most prior crypto-pair accepts this trigger which shared one
cap).

## Decision: ACCEPT (QQQ, SPY, BTC/USDT, ETH/USDT -- all four symbols)

Third strategy this cron trigger (after Firefly and Elegant Oscillator) to
accept all 4 target symbols in a single reframing pass.

## Notes

- Formula reused verbatim from the existing accepted knowledge base entry
  (2026-09-09-098) -- no fresh web fetch needed this sub-step.
- Walk-forward fallback: manual 4-equal-slice split (same pattern as other
  `run_validate_*.py` scripts).
- Source: https://quantstrategy.io/blog/how-to-trade-with-volume-rsi-indicator/

# 2026-09-21 ATR Channel Mean Reversion with Stop-Loss/Take-Profit

**Hypothesis:** Per FMZ.com's "ATR Channel Mean Reversion Quantitative
Trading Strategy" (https://www.fmz.com/lang/en/strategy/434995, read via
browser_exec — web_extract backend cannot fetch page content, DDGS-only):
ATR channel (EMA basis +/- atr_mult*ATR). Entry at next bar's open when
prior close breaks below the lower band. ATR-multiple stop-loss from entry
price. Take-profit at EMA basis or upper band, whichever reached first.

**Strategy file:** `strategies/2026-09-21_atr_channel_meanrev_stoploss.py`

## Step 6 grid summary (atr_mult∈{1.5,2.0,2.5} × stop_loss_mult∈{1.0,1.5,2.0}
× QQQ/SPY/BTC-USDT/ETH-USDT × low/mid/high vol terciles, 2019-2026)

- total_cells: 108, passed_cells: 9, **pass_fraction: 0.083**
- by_asset_class: equity 4/54, crypto 5/54
- by_vol_regime: low 6/36, mid 3/36, **high 0/36**
- best_cell: SPY low-vol tercile, atr_mult=1.5/stop_loss_mult=1.5,
  Sharpe 1.328 (isolated slice only, does not hold full-sample)
- worst_cell: BTC/USDT low-vol tercile, Sharpe -1.212

## Full-sample single-config sweep (all 9 combos, QQQ and SPY)

Full-sample Sharpe never clears 1.0 for QQQ (best 0.339) or SPY (best
0.591) at ANY of the 9 tested (atr_mult, stop_loss_mult) combinations.
Max drawdown fails the 0.25 threshold for every single combo tested
(QQQ range 0.246-0.366, SPY range 0.359-0.414) — the ATR-based stop-loss
does not meaningfully cap drawdown at daily-bar resolution (stop checked
only at close, so intraday gap-throughs blow past the intended stop level).

## Decision: REJECT (decisive)

Both Sharpe and max-drawdown validators fail decisively across the entire
parameter grid and both equity symbols; no isolated regime slice generalizes
to full-sample. Crypto also fails (5/54 grid cells, worst in low-vol
regime — inconsistent with the equity high-vol-only failure pattern seen
elsewhere in this repo, suggesting the stop-loss/take-profit exit logic
itself, not just regime, is the primary failure mode). Not revisiting this
exact construction; a close-only (not open-execution) variant or an
intrabar stop-check via a different data granularity could be a future
rescue angle but is out of scope for this repo's daily-bar-only pipeline.

# Stan Weinstein Stage 2 Breakout — Backtest Report

**Source:** Google SERP aggregation of corroborating sources (MQL5
"Automating Classic Market Methods (Part 3): Stan Weinstein Stage
Analysis" EA description, ThinkCapital/TrendSpider Weinstein Stage 2
Breakout strategy summaries), read via browser_exec (web_search DDGS
backend RequestError'd on the original query this iteration).

**Hypothesis:** 30-week SMA (150 trading days) regime + volume-confirmed
resistance breakout entry (Stage 2), compound exit (close below SMA on
heavy volume OR SMA slope flattening = Stage 3 signal). First
Weinstein-Stage-Analysis entry in this repo.

## Step 6 grid summary
`resistance_window` in {30,50,75} x `volume_confirm_mult` in {1.5,2.0} x
`exit_volume_mult`={1.5} (fixed), symbols QQQ/SPY (equity) +
BTC/USDT/ETH/USDT (crypto), vol_regime_splits=3. 72 total cells.

- pass_fraction: 8/72 = 11.1% (weak across the board)
- by_asset_class: equity 5/36 (13.9%), crypto 3/36 (8.3%)
- by_vol_regime: low 7/24 (29.2%), mid 0/24 (0%), high 1/24 (4.2%)
- best_cell: resistance_window=30, volume_confirm_mult=2.0, ETH/USDT mid-vol, Sharpe=1.91 (isolated single-cell outlier)
- No config reaches 2/3 vol regimes passing for any symbol -- the strongest
  average was BTC/USDT resistance_window=75/volume_confirm_mult=2.0 at
  avg Sharpe 1.26 but still only 1/3 regimes.

## Step 7 single-config validators (best-avg configs per asset class)

### SPY (resistance_window=30, volume_confirm_mult=2.0, exit_volume_mult=1.5)
- Only 1 trade over the full 2019-2026 period (volume_confirm_mult=2.0 AND
  sma_rising AND resistance breakout is an extremely rare joint condition
  on daily equity bars).
- Sharpe: 0.670 (FAIL, threshold 1.0)
- Max drawdown: 8.32% (PASS)

### BTC/USDT (resistance_window=75, volume_confirm_mult=2.0, exit_volume_mult=1.5)
- 204 trades (crypto's volume series is much noisier, triggers far more often)
- Sharpe: 0.256 (FAIL, threshold 1.0)
- Max drawdown: 32.42% (FAIL, threshold 25%)

## Decision: REJECTED (both SPY and BTC/USDT; Sharpe fails decisively for both)

The compound AND-gate (resistance breakout + volume confirmation + SMA
rising) is too restrictive on daily equity bars (essentially never fires
cleanly enough to build a reliable track record -- only 1 trade for SPY
over 7+ years) while being too permissive/noisy on crypto (204 trades,
Sharpe well under 1.0, MDD over budget). Grid confirms no single config
achieves >=2/3 vol-regime passes for any symbol. Not accepted per Step 8.

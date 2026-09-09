# 2026-09-10 — GDX/RING Gold-Miner ETF Cointegration Pairs Trade

## Hypothesis

VanEck Gold Miners ETF (GDX) and iShares MSCI Global Gold Miners ETF (RING)
track overlapping baskets of gold-mining companies, so their return spread
is economically "tethered" and should mean-revert. Per
https://onepagecode.substack.com/p/quant-trading-strategies-exploiting-mean-reversion-gold-miner-etfs
(OnePageCode's 365-day quant series #7), a rolling-window return-spread
z-score with liquidity-adjusted sizing and month-end forced exit captures
this convergence. Implemented here reusing the repo's existing rolling-OLS-
hedge-ratio z-score pairs framework (first used for JPM/BAC in
`2026-09-08_pairs_zscore_cointegration.py`) with GDX as the primary/tradable
leg and RING as the partner — the first gold-miner-ETF pairs trade in this
repo, distinct from JPM/BAC, V/MA, ETH/BTC, SPY/QQQ, and BTC/gold pairs
already tested.

Strategy file: `strategies/2026-09-10_gdx_ring_gold_miner_pairs.py`
(equity-only — no crypto analogue for gold-miner ETF pairs).

## Single-config validator results (hedge_window=30, z_window=30, entry_z=1.2, exit_z=0.5, max_hold_days=3)

| Symbol | Sharpe | MDD | Net Sharpe (10bps/trade) | Walk-forward pass fraction | Trades |
|---|---|---|---|---|---|
| GDX (vs RING) | 1.104 (pass, thr 1.0) | 0.154 (pass, thr 0.25) | 0.885 (pass, thr 0.5) | 1.00 (pass, thr 0.75; 4/4 splits) | 181 |

Parameter sensitivity (10-cell Sharpe grid across entry_z x max_hold_days x
z_window near the local optimum, GDX): relative std = 0.065, threshold 0.5
→ **pass** — very robust to reasonable parameter perturbation.

Note: `check_walk_forward` computed via a manual 4-way `np.array_split`
range-split substitute (same as prior iterations this trigger) due to the
pre-existing `vectorbt.utils.splitting` AttributeError on installed
vectorbt 1.1.0 (flagged in 2026-09-10-021).

## Step 6 grid summary (entry_z x max_hold_days x GDX x low/mid/high vol terciles)

- 27 cells, 10 passed (pass_fraction 0.370), equity only.
- By vol regime: low 3/9, mid 3/9, high 4/9 — reasonably even distribution,
  not concentrated in one regime.
- Best cell: entry_z=1.2, max_hold_days=3, high-vol tercile, Sharpe 1.934.
- Worst cell: entry_z=2.0, max_hold_days=10, low-vol tercile, Sharpe -0.214.

## Decision: ACCEPT (equity — GDX/RING pair)

All validators pass for the primary config (Sharpe 1.104, MDD 0.154, net
Sharpe after 10bps costs 0.885, walk-forward 4/4, parameter-sensitivity
relative std 0.065). Only one leg (long GDX) is expressed as a tradable
0/1 position series per the repo's convention; RING is fetched internally
purely to compute the spread/hedge-ratio, matching the existing pairs-trade
pattern in this repo. No crypto analogue tested (gold-miner ETFs have no
comparable crypto pair).

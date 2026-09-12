# Backtest Report: Weekend-Gated 7-Day Crypto Momentum (2026-09-13)

## Hypothesis
Per Kumari, Wasan & Chhimwal (2025), "The Weekend Effect in Crypto
Momentum: Does Momentum Change When Markets Never Sleep?" (Advances in
Consumer Research, https://acr-journal.com/article/the-weekend-effect-in-crypto-momentum-does-momentum-change-when-markets-never-sleep--1514/,
read via browser_exec), a 7-day momentum strategy on 10 major
cryptocurrencies shows weekend returns significantly exceed weekday
returns (p<0.05 for all coins tested), with better Sharpe and MDD.
Long-only adaptation: hold a positive 7-day-momentum long signal ONLY on
weekend calendar days (Sat/Sun UTC), flat otherwise.

Source URL: https://acr-journal.com/article/the-weekend-effect-in-crypto-momentum-does-momentum-change-when-markets-never-sleep--1514/

## Strategy file
strategies/2026-09-13_crypto_weekend_gated_momentum.py

## Step 6 grid summary (QQQ/SPY/BTC-USDT/ETH-USDT, mom_lookback=[3,5,7,14], vol_regime_splits=3, 2018-2026)

- total_cells: 48, passed_cells: 0, pass_fraction: 0.0 (decisive failure)
- by_asset_class: equity 0/24 (expected -- equity has no weekend bars, degenerate all-flat-most-of-time signal), crypto 0/24
- by_vol_regime: low 0/16, mid 0/16, high 0/16 (uniform failure)
- best_cell: mom_lookback=14, ETH/USDT, high-vol regime, Sharpe only 0.206
- worst_cell: mom_lookback=5, BTC/USDT, mid-vol regime, Sharpe -0.293

## Decision: REJECTED at grid stage (decisive, no near-miss)

0/48 grid cells pass across all parameter values, asset classes, and
volatility regimes; best cell Sharpe (0.206) is far below the 1.0
threshold. Per RESEARCH_LOOP.md Step 7, this decisive grid failure does
not warrant the full single-config validator suite. Likely explanation:
the source paper's own reported Sharpe ratios (weekend Sharpe ~0.07,
weekday ~0.035, using zero risk-free rate and NOT annualized the way this
repo's validators.py does) are extremely low in absolute terms even in the
paper's own framing -- the "significant" weekend outperformance the paper
finds is a relative comparison between two already-weak absolute Sharpe
ratios, not evidence that either regime clears a standard annualized
Sharpe >= 1.0 bar. Restricting trading to only 2 of 7 days a week also
sharply reduces compounding opportunity versus an unconditional momentum
strategy.

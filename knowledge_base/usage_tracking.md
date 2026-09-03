# Cronjob Usage Tracking Log

Manual measurement of Claude 5h rolling window `used_percent` (via Hermes
`agent.account_usage.fetch_account_usage`) before/after each research loop
run, to empirically estimate per-run consumption for the hourly cronjob
(`quant-agent-research-loop`, job_id 7252d5c819b0).

| Timestamp (KST) | Event | usage_pct (5h window) | delta |
|---|---|---|---|
| 17:53 | before manual run #1 (first-ever loop, heavy debugging) | 32.0% | - |
| 17:56 | after manual run #1 | 36.0% | +4.0% |
| 18:10 | baseline before cron run #1 (manual trigger via `run`) | 36.0% | - |
| 18:12 | after cron run #1 (manual trigger, BTC momentum, rejected on MDD) | 38.0% | +2.0% |
| 18:15 | after cron run #2 (BTC momentum + inverse-vol sizing, rejected on MDD) | 38.0% | +0.0% (rounded; API reports whole percents) |
| 18:47 | after 1x-limited test run (research pipeline: web search + grid test, ~5min duration) | 46.0% | +8.0% |

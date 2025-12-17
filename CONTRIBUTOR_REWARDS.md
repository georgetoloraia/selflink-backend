# Contributor Rewards

For the full model and examples, see `docs/CONTRIBUTOR_REWARDS.md`.

- Reward events are append-only (`RewardEvent` ledger).
- Monthly snapshots and payouts are calculated deterministically.
- Corrections are made via new events, not edits.

## Issue-based rewards (planned)
- Each GitHub Issue will have a predefined score.
- Score is assigned before work begins.
- Score is immutable once captured.
- Completing the issue via a merged PR awards the score.
- Implementation is pending and tracked via GitHub issue.

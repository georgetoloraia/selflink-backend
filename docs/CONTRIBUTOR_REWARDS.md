## Contributor Rewards & Revenue Sharing
SelfLink is built on a simple principle:

> Contributors should share directly and transparently in the value they help create.

This document explains how contributors are rewarded, how payouts are calculated, and what guarantees exist around fairness and transparency.

# 1. High-level commitment
From day one, SelfLink commits to the following rule:

50% of all net platform revenue is reserved for contributors.

- This is not discretionary.

- This is enforced at the architecture and accounting level.

- This rule will not be changed retroactively.

The remaining 50% is used for:

- infrastructure and hosting

- LLM and compute costs

- maintenance and long-term stability of the platform

# 2. What counts as a contribution?
At launch, rewards are granted for merged GitHub pull requests only.

Examples:

- backend code (Django, Celery, infra)

- mobile code (React Native)

- tests

- documentation

- security, performance, or infra improvements

Other contribution types (bounties, community moderation, design, etc.) may be added later, but PRs are the initial, objective unit of contribution.

# 3. How contributions are recorded (append-only ledger)
Every rewarded contribution becomes a RewardEvent in an append-only ledger.

Key properties:

- Events are immutable (never edited or deleted).

- Corrections are handled via new events, never by rewriting history.

- Every event links to:

- - a GitHub PR URL

- - the contributor identity

- - the rules version used to score it

- - a cryptographic hash of the source payload (for auditability)

This design ensures that:

- payouts are reproducible

- history is verifiable

- trust does not depend on a human decision after the fact

# 4. How points are assigned (deterministic rules)

Each merged PR receives points, based on its labels.

Default size-based scoring (example v1)

| Label   | Points |
| ------- | ------ |
| size:xs | 1      |
| size:s  | 3      |
| size:m  | 5      |
| size:l  | 8      |
| size:xl | 13     |

- A PR must have exactly one size:* label to be scored.

- Missing size labels result in 0 points until corrected.

- Optional small bonuses may exist (e.g. security, infra), but are intentionally limited.

Rule versioning

- Each RewardEvent stores the rules version used.

- If rules change in the future, past rewards are not recalculated.

- This guarantees predictability and fairness over time.

# 5. Monthly reward snapshots

Rewards are calculated monthly.

For each month:

1. All RewardEvents in that period are aggregated.

2. Total points across all contributors are computed.

3. The contributor reward pool (50% of net revenue) is fixed.

4. Each contributor’s share is calculated deterministically:

```
contributor_share = (contributor_points / total_points) × reward_pool
```

The result is stored in a MonthlyRewardSnapshot, which includes:

- total revenue

- total contributor pool

- total points

- per-contributor payouts

- snapshot hash (for auditability)

# 6. Payouts

Each contributor receives a Payout record per month when eligible.

- Payouts are derived strictly from the snapshot math.

- Minimum payout thresholds may apply (to avoid dust payments).

- Payment methods (e.g. bank transfer, PayPal, crypto) are defined separately.

- Payout status is tracked (`pending`, `processing`, `paid`).


Example:
> - Revenue: $1,000
> - Contributor pool (50%): $500
> - Alice: 13 points → $260
> - Bob: 8 points → $160
> - Carol: 4 points → $80

# 7. Dispute window & corrections

After a monthly snapshot is generated:

- A fixed dispute window (e.g. 7 days) is opened.

- Contributors may raise issues about:

- - missing PRs

- - incorrect labels

- - identity mapping problems

After the dispute window closes:

- The snapshot is locked.

- Corrections are made via new RewardEvents (e.g. adjustments), never by editing old data.

# 8. Identity & eligibility

To receive rewards:

- You must link your GitHub username to a SelfLink account.

- Rewards are assigned to the PR author, not the merger.

- If no linked identity exists at ingestion time, the event is recorded but not paid until resolved.

# 9. Transparency guarantees

SelfLink commits to the following:

- Reward calculations are deterministic and reproducible.

- Ledger data and monthly summaries are exportable.

- No hidden coefficients, manual overrides, or secret bonuses.

- No retroactive rule changes.

- No silent reallocations of the contributor pool.

>Trust is enforced by design, not promises.

# 10. What this system is (and is not)

This system is:

- an experiment in sustainable open-source funding

- intentionally boring, mechanical, and auditable

- designed to minimize subjective decisions

This system is not:

- a token sale

- a DAO

- a speculative investment

- a promise of guaranteed income

Rewards depend on:

- actual platform revenue

- actual contributions

- transparent, fixed rules

# 11. Why we are doing this

> Most social platforms extract value from users and contributors without sharing it.

SelfLink exists to test a different idea:

> If people can trust the system, they will help build it.

> >This reward model is our attempt to earn that trust.

# 12. Feedback and evolution

This model will evolve, but:

- changes will be discussed publicly

- new rules will only apply going forward

- historical rewards will remain untouched

If you have suggestions, critiques, or improvements:

- open an issue

- start a discussion

- or propose a change via PR

We welcome hard questions.

> Thank you for contributing.
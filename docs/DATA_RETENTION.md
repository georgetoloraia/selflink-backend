# Data Retention Policy (SelfLink Backend)

This policy documents what we keep, for how long, and what still needs enforcement in code/infra.

## Defaults
- Mentor chats & LLM prompts: 90 days (TODO: add automated purge job + anonymized analytics option).
- Astrology/matching calculations: cacheable, non-PII outputs may be kept indefinitely; source birth data is user-controlled and should be deletable on request.
- Logs/metrics: 30 days for app logs, 7 days for request traces; never log request bodies or secrets.
- Media uploads: stored in S3/MinIO; keep until user deletes content or account, subject to DMCA/legal holds.
- Contributor rewards ledger: append-only, kept indefinitely for auditability; monthly CSV + hash published per snapshot.
- Payments/subscriptions: follow payment processor requirements; retain minimal metadata only.

## Requests & Deletion
- Users can request account deletion; purge PII tables (see `apps.users.models.UserPII`) and orphaned media.
- Birth data and mentor history must be removed on deletion; cached astro results should be invalidated.

## Open TODOs
- Implement scheduled tasks to purge mentor chats >90 days and rotate logs.
- Enforce retention windows in S3 buckets (lifecycle rules) and Redis caches.
- Document legal hold/backup procedures and how to verify deletions end-to-end.

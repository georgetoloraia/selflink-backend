# SLC Wallet (SelfLink Coin)
SLC is an internal, off-chain credit system pegged 1:1 to USD.
Balances are integer cents only; no floats.
Every user gets a CoinAccount automatically on registration.
All ledger rows are append-only and immutable; history is never rewritten.
All postings are double-entry and must balance to zero per currency.
Ledger pagination is ordered by (created_at, id); `next_cursor` is opaque base64url JSON `{ts,id}` and legacy numeric cursors are accepted (invalid cursors return 400).
P2P transfers and internal spending are supported; transfer fees apply.
System accounts (mint/fees/revenue) are fixed and created via migrations.
Payment→SLC conversion is internal-only and idempotent by provider event ID; there is no public mint endpoint.
SLC is NOT a blockchain token and has no on-chain representation.
Withdrawals to fiat/crypto are not implemented and are out of scope.
Snapshots are deterministic and hash-verified for auditability.

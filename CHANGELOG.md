# Changelog

All notable changes to this project will be documented here.

## [0.0.2] — 2026-04-25

Initial Postgres schema (`migrations/0001_init_schema.sql`).

- Tables: `leads`, `email_drafts`, `email_sends`, `lead_events`,
  `unsubscribes`, `agent_memory` (pgvector + tsvector).
- Views: `funnel_v` (drives `/leads stats`), `recipe_lift_v`
  (drives `/recipes lift`), `daily_send_count_v` (warm-up cap enforcer).
- Extensions: `pgcrypto`, `vector`, `pg_trgm`.
- Append-only `lead_events` log + immutable snapshot in `email_sends`
  (subject/body) for CASL audit.
- Hard-stop CASL `unsubscribes` table — pre-flight check before every send.
- Drop alembic from deps; raw-SQL migrations applied with psql, same as
  the ads agent.

## [0.0.1] — 2026-04-25

Initial scaffold.

- Public engine package (`sales_agent`) with module skeleton:
  `discovery/`, `enrichment/`, `agent/`, `mail/`, `discord/`, `db/`.
- Stub recipe library (`sales_agent.agent.recipes_stub`) — generic placeholders.
- Resolution layer (`sales_agent.agent.recipes`) — imports from
  `glitch_grow_sales_playbook` (private package) when available, falls back to
  stubs otherwise.
- README, Dockerfile, BSL 1.1 LICENSE, `.env.example`, pyproject.toml.
- No implementation — graph nodes, Gmail send, Discord bot are stubbed and
  tracked in the v1 milestone.

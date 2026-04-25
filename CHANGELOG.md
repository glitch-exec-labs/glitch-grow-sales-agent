# Changelog

All notable changes to this project will be documented here.

## [0.0.4] — 2026-04-25

HubSpot CRM mirror (one-way, Postgres canonical).

- migrations/0002_hubspot_links.sql — adds `hubspot_contact_id`,
  `hubspot_company_id`, `hubspot_deal_id`, `hubspot_synced_at` to
  `leads`; `hubspot_engagement_id` to `email_sends`. Indexed for
  re-resolution from webhook payloads.
- src/sales_agent/hubspot/ — module:
  - `client.py` — raw httpx v3 REST client with PAT bearer auth and
    tenacity retries on 429 / 5xx / transport errors.
  - `stages.py` — single source of truth for the Glitch Budz pipeline
    (9 stages) and `leads.status → HubSpot stage` mapping. `opened`
    deliberately maps to `Sent` because we don't surface opens.
  - `mapper.py` — pure transforms: lead → contact / company / deal
    payloads; send → email engagement payload.
  - `pipelines.py` — idempotent bootstrap: ensures the pipeline,
    stages, and custom properties (current_site_status, agent_score,
    agco_license) exist.
  - `sync.py` — public surface: `sync_lead`, `sync_send`, `sync_reply`.
    Failures log + swallow so Postgres writes are never rolled back.
    Per-process pipeline/stage id cache.
  - `bootstrap_pipeline.py` — one-shot setup runner.
- LeadRepo.set_hubspot_ids() — persists ids back after sync.
- SendRepo.set_hubspot_engagement() — persists engagement id.
- Config: HUBSPOT_PAT, HUBSPOT_PIPELINE_NAME, HUBSPOT_SYNC_ENABLED,
  HUBSPOT_PORTAL_ID.
- `.env.example` updated with rotation guidance.

## [0.0.3] — 2026-04-25

DB access layer.

- src/sales_agent/db/pool.py — asyncpg pool singleton with pgvector
  adapter registration on every connection.
- src/sales_agent/db/models.py — Pydantic v2 models with Literal-typed
  enums for funnel state, recipe key, current_site_status, approval
  state, etc. mypy enforces parity with the SQL CHECK constraints.
- src/sales_agent/db/repos.py — async repos for all six tables.
  `LeadRepo.transition` does the status update + lead_event insert in
  one transaction with `SELECT ... FOR UPDATE` so concurrent transitions
  linearize. `SendRepo.daily_count` excludes follow-ups (initial-send
  reputation only). `MemoryRepo` recall is most-recent-N for now;
  hybrid vector + FTS lands when the embedding worker is online.

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

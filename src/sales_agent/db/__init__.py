"""Postgres access layer.

Owns the `sales_agent.*` schema (asyncpg pool, repos, agent_memory with
pgvector). Migrations live under `migrations/` and are managed with Alembic.

Tables (to be created in the v1 migration):
- `sales_agent.leads`         — every prospect, with enrichment + status.
- `sales_agent.email_drafts`  — every drafted email + recipe + subject variant.
- `sales_agent.email_sends`   — every send + tracking pixel id + reply state.
- `sales_agent.lead_events`   — funnel-state-transition log.
- `sales_agent.agent_memory`  — pgvector + tsvector decision log.
"""

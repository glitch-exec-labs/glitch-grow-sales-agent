# Changelog

All notable changes to this project will be documented here.

## [0.0.1] — 2026-04-25

Initial scaffold.

- Public engine package (`sales_agent`) with module skeleton:
  `discovery/`, `enrichment/`, `agent/`, `mail/`, `discord/`, `db/`.
- Stub recipe library (`sales_agent.agent.recipes_stub`) — generic placeholders.
- Resolution layer (`sales_agent.agent.recipes`) — imports from
  `glitch_grow_sales_playbook` (private package) when available, falls back to
  stubs otherwise.
- README, Dockerfile, BSL 1.1 LICENSE, `.env.example`, pyproject.toml.
- No implementation — graph nodes, Gmail send, Discord bot, and Postgres
  schema are stubbed and tracked in the v1 milestone.

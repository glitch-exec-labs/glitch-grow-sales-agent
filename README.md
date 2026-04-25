# Glitch Grow AI Sales Agent

> **An autonomous outbound sales agent for productized SaaS** — discovers prospects, enriches them, drafts personalized email per a recipe library, escalates to a human via Discord, sends through Gmail, tracks replies, and learns from outcomes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestrator-LangGraph-orange)](https://github.com/langchain-ai/langgraph)
[![License: BSL 1.1](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](LICENSE)
[![Cloud Run ready](https://img.shields.io/badge/deploy-Cloud%20Run-4285F4?logo=google-cloud)](https://cloud.google.com/run)

---

> Part of **Glitch Grow**, the digital marketing domain inside **Glitch Executor Labs** — one builder shipping products across **Trade**, **Edge**, and **Grow**.

## What this is

An **autonomous AI agent** that runs outbound sales for a productized SaaS. The agent closes the full loop — it discovers prospects, enriches them with public data, drafts a personalized email per a tunable recipe library, escalates each draft to a human approver via Discord, sends through Gmail once approved, tracks opens and replies, follows up on silence, and writes every decision to a memory store so the operator's interventions become training signal.

```
       ┌─────────────────────────────────────────────────────────┐
       │                                                         │
       │   DISCOVER   →   ENRICH   →   SCORE   →   DRAFT         │
       │   (Google         (current-      (priority   (recipe     │
       │    Maps +          site +         heuristic)  library)   │
       │    AGCO)           contact)                              │
       │       ▲                                       │         │
       │       │                                       ▼         │
       │     LEARN  ◄──────  TRACK  ◄──── SEND ◄──── HITL         │
       │   (memory:         (opens +    (Gmail)    (Discord       │
       │    decisions,       replies)               approval)     │
       │    recipe lift)                                          │
       └─────────────────────────────────────────────────────────┘
```

The human is the **supervisor**: every draft goes to Discord with one-tap approve / reject / request-edit reactions. The agent's autonomy threshold can be raised per-recipe once a recipe earns enough approvals. Replies are surfaced as a thread to the operator, with the full lead context attached.

The first deployment is **Glitch Budz** — a productized cannabis e-commerce SaaS targeted at independent Toronto cannabis retailers. The agent is generic enough to retarget any productized SaaS by swapping the [private playbook package](#private-playbook-pattern) — the public engine ships with stub copy and a stub recipe library.

---

## Features

### Autonomous outbound loop
- Discovers prospects from Google Maps Places API, cross-checks against the AGCO Cannabis Retail Store registry (or another source-of-truth registry), dedups against the existing pipeline.
- Enriches each lead with a `current_site_status` enum (`none / linktree / builder / lightspeed / custom`) by fetching the prospect's website and pattern-matching well-known signatures.
- Resolves a contact email by scraping the website footer, checking IG bio, then falling back to MX-verified pattern guesses (`info@`, `hello@`).
- Scores the lead by a heuristic that prioritizes shops with the weakest current sites (highest pitch-fit).
- Drafts an email by selecting a recipe from the library keyed on `current_site_status`, then routing the prompt through LiteLLM (Claude Sonnet for reasoning).

### Human-in-the-loop on Discord
- Every draft is posted as an embed in a configured Discord channel. One reaction sends, one rejects, one opens an inline edit request.
- Per-recipe **autonomy thresholds**: once a recipe has N approved drafts in a row, the agent earns the right to auto-send within a per-day cap. Below threshold, every draft is HITL.
- Replies from prospects are surfaced as a fresh Discord post with the full thread + lead enrichment summary, ready for the operator to compose a response (also HITL-drafted).

### Recipe library
- Per-`current_site_status` recipes hold the opener line, value-prop emphasis, and proof reference.
- Subject-line A/B variants are first-class: each recipe can ship N subjects and the tracker measures open-rate per subject.
- Public engine ships **stub recipes** in `sales_agent.agent.recipes_stub`. The [private playbook package](#private-playbook-pattern) overrides them with the real, tuned, brand-specific copy.

### Memory + learning
- `sales_agent.agent_memory` (Postgres + pgvector + tsvector FTS) — every draft, every approval/edit, every reply, every outcome indexed.
- Every draft prompt injects `<prior_context>` — "the last time we hit a Linktree-shop in midtown, the operator edited the opener to X and the recipient replied" — so the LLM's defaults converge on what actually works for the operator.
- Nightly consolidation cron promotes durable lessons (winning subject lines, edit patterns, dead-zone neighbourhoods) into a per-product `MEMORY.md` loaded as system context.

### Send + track via Gmail API
- Sends from a real human Gmail / Google Workspace mailbox — no transactional ESP, replies thread naturally.
- Open-tracking via 1×1 pixel; reply-tracking via Gmail API thread polling.
- CASL-compliant footer is enforced at send time (sender name, business address, working unsubscribe).

---

## Architecture

```
                     Discord (operator)
                           ▲
                           │ approvals · edit requests · replies
                           ▼
              ┌────────────────────────────┐
              │   LangGraph Sales Core     │   discover → enrich → score → draft → HITL → send → track → follow-up
              │   per-turn <prior_context> │   LiteLLM: Claude Sonnet → Gemini Flash → cheap fallback
              │   • discovery nodes        │
              │   • enrichment nodes       │
              │   • drafter (recipe lib)   │
              │   • HITL approval gate     │
              │   • sender (Gmail API)     │
              │   • tracker (open + reply) │
              │   • memory (pgvector+FTS)  │
              └──────┬─────────────────────┘
                     │
       ┌─────────────┼──────────────────┬────────────────┐
       ▼             ▼                  ▼                ▼
  Google Places  AGCO Registry     Postgres          Gmail API
  (discovery)    (license cross-   (sales_agent.*    (send + read for
                  check)            schema)           reply detection)
```

**Deployment split:**
- **Cloud Run** — LangGraph agent HTTP endpoint (`/agent/run`), Cloud Scheduler jobs (daily discovery sweep, daily follow-up cron).
- **VM / systemd** — Discord bot (long-lived gateway connection) + Gmail reply poller. Discord bots can't run scale-to-zero.
- **Postgres** — `sales_agent.*` schema with pgvector + tsvector. Same instance can host other Glitch Grow agents' schemas.

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Agent orchestration | [LangGraph](https://github.com/langchain-ai/langgraph) | Durable state machine, retries, HITL gates — same orchestrator as the [ads agent](https://github.com/glitch-exec-labs/glitch-grow-ads-agent) for operational consistency |
| Typed tool schemas | [Pydantic AI](https://github.com/pydantic/pydantic-ai) | Validated I/O for lead objects + draft objects |
| LLM routing | [LiteLLM](https://github.com/BerriAI/litellm) | Claude Sonnet for drafting, Gemini Flash for bulk classification, cheap fallback for parse-only |
| Discovery | Google Maps Places API | Per-neighbourhood polygon search, gives website + phone + hours |
| Compliance cross-check | AGCO Cannabis Retail Store registry (Ontario) | Filters the Places list down to actually-licensed shops |
| Memory | Postgres + pgvector + tsvector | Hybrid recall (semantic + keyword) on every draft |
| Email send/read | Gmail API (Google Workspace) | Real human inbox, reply threading, no ESP middleman |
| HITL surface | [discord.py](https://github.com/Rapptz/discord.py) | Mobile-friendly, reaction-based UX, gateway connection |
| Web server | FastAPI + uvicorn | Healthz, agent run endpoint, Discord interaction webhook |
| Hosting | Google Cloud Run + Cloud Scheduler | Scale-to-zero for the agent core; VM for the Discord bot |

---

## Quickstart

### Prerequisites

- Python 3.11+
- Postgres 16+ with the `vector` extension (pgvector ≥ 0.7)
- Google Cloud project with Places API enabled
- Google Workspace mailbox + Gmail API OAuth credentials
- Discord application + bot token
- Anthropic API key (Claude) and/or Google AI Studio key (Gemini)

### Install

```bash
git clone https://github.com/glitch-exec-labs/glitch-grow-sales-agent.git
cd glitch-grow-sales-agent

# Install deps (uv recommended)
uv sync
# or: python -m venv .venv && pip install -e .
```

### Configure

```bash
cp .env.example .env
# Edit .env — every key is documented in the example file
```

Key variables in `.env`:

| Variable | What it is |
|---|---|
| `POSTGRES_RW_URL` | Writable Postgres role that owns `sales_agent.*` (leads, drafts, sends, agent_memory). |
| `GOOGLE_PLACES_API_KEY` | GCP API key with Places API enabled. |
| `GMAIL_OAUTH_CLIENT_ID` / `GMAIL_OAUTH_CLIENT_SECRET` / `GMAIL_OAUTH_REFRESH_TOKEN` | OAuth credentials for the sending mailbox. |
| `GMAIL_SENDER_EMAIL` | The From address (e.g. `tejas@glitchexecutor.com`). |
| `DISCORD_BOT_TOKEN` | Discord application bot token. |
| `DISCORD_GUILD_ID` / `DISCORD_APPROVAL_CHANNEL_ID` | Where draft approvals are posted. |
| `DISCORD_ADMIN_USER_IDS` | Comma-separated Discord user IDs allowed to approve sends. |
| `ANTHROPIC_API_KEY` | For Claude Sonnet (drafter). |
| `GOOGLE_API_KEY` | For Gemini Flash (bulk classification, fallback). |
| `AGENT_RUN_TOKEN` | Bearer token required to call `POST /agent/run`. |
| `CASL_SENDER_NAME` / `CASL_SENDER_ADDRESS` | Required CASL footer on every outbound email. |
| `OUTREACH_DAILY_CAP` | Hard ceiling on emails sent per day (warm-up cadence enforced server-side). |

### Set up Postgres

```sql
CREATE USER sales_agent_rw WITH PASSWORD 'choose_strong_password';
CREATE SCHEMA sales_agent AUTHORIZATION sales_agent_rw;
GRANT USAGE, CREATE ON SCHEMA sales_agent TO sales_agent_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA sales_agent TO sales_agent_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA sales_agent TO sales_agent_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA sales_agent
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sales_agent_rw;

-- pgvector
CREATE EXTENSION IF NOT EXISTS vector;
```

Then run migrations (Alembic — `migrations/` directory):

```bash
alembic upgrade head
```

### Run locally

```bash
# FastAPI server (agent run endpoint, healthz)
uvicorn sales_agent.server:app --reload --port 3120

# Discord bot in long-lived process
python -m sales_agent.discord.bot
```

### Deploy

- **Agent core** to Cloud Run, IAM-private, called by Cloud Scheduler.
- **Discord bot** to a VM (or Cloud Run with `--min-instances=1` if you want to pay for that).
- **Reply poller** as a Cloud Scheduler → Cloud Run job that polls Gmail every 5 minutes.

See `ops/` for systemd units and Dockerfile.

---

## Private playbook pattern

The public engine ships with **deliberately-generic placeholder copy** in `sales_agent.agent.recipes_stub` — every recipe says something like *"Hi, we built a thing."* This is intentional: the brand-specific pitches, A/B subject lines, and tuned send caps live in a separate **private package** that overrides the stubs at import time.

```python
# src/sales_agent/agent/recipes.py (resolution layer)

try:
    from glitch_grow_sales_playbook.recipes import RECIPES
except ImportError:
    from sales_agent.agent.recipes_stub import RECIPES
```

Install the private package on the production VM only:

```bash
pip install git+ssh://git@github.com/glitch-exec-labs/glitch-grow-sales-agent-private.git@main
```

When the private package is importable, the agent uses real Glitch Budz copy. When it's not (public-only dev clone, contributor PR), the engine falls back to the stub — runnable, but unhelpful for actual selling. This means the public repo can be open-source-friendly without leaking the operator's edge.

Same pattern as [glitch-grow-ads-agent-private](https://github.com/glitch-exec-labs/glitch-grow-ads-agent-private).

---

## Telegram-equivalent: Discord commands

| Command | What it does |
|---|---|
| `/leads new <count>` | Discover N new prospects from Places + AGCO, write to `leads`. |
| `/leads stats` | Funnel snapshot: discovered → enriched → drafted → sent → opened → replied → booked. |
| `/draft <lead_id>` | Show the proposed draft for a single lead, approve / edit / reject inline. |
| `/pause <lead_id>` | Stop the sequence for one lead. |
| `/autonomy <recipe> <threshold>` | Set per-recipe auto-send threshold. |
| `/recipes lift` | Show open + reply rates per recipe + subject-line variant. |

All commands are Discord slash commands. Approval/reject/edit on individual drafts is reaction-based on the embed message — `✅` to send, `❌` to kill, `🖊️` to request an edit (operator replies to the embed thread with the new copy).

---

## Project layout

```
src/sales_agent/
  config.py              # Settings + constants (no per-prospect config — that lives in DB)
  server.py              # FastAPI: /healthz, /agent/run, /discord/interaction (if using webhook mode)
  discovery/
    google_places.py     # Per-neighbourhood Places API search
    agco.py              # AGCO licensee registry cross-check
  enrichment/
    site_detector.py     # current_site_status enum classifier
    contact_finder.py    # email resolution: scrape footer → IG bio → MX-verified pattern guess
  agent/
    graph.py             # LangGraph state machine (discover → enrich → score → draft → HITL → send → track → follow-up)
    llm.py               # LiteLLM model router (Claude Sonnet / Gemini Flash / cheap fallback)
    recipes.py           # Resolution layer: tries private playbook, falls back to stub
    recipes_stub.py      # Placeholder recipes (public, generic)
    nodes/               # One file per graph node
  mail/
    gmail.py             # Gmail API send + read
    tracker.py           # Open-pixel + reply detection
  discord/
    bot.py               # discord.py bootstrap
    handlers.py          # Slash commands + reaction handlers
    auth.py              # DISCORD_ADMIN_USER_IDS guard
  db/
    pool.py              # asyncpg pool
    repo.py              # Lead / draft / send repos
  scheduler/
    follow_up.py         # 4-day + 10-day no-reply nudges
ops/
  systemd/               # systemd units (Discord bot, Gmail poller)
  scripts/               # bootstrap_postgres.py, register_discord_commands.py
playbooks/               # Operational runbooks (warm-up cadence, deliverability, kill switches)
migrations/              # Alembic
tests/                   # pytest suite
```

---

## Roadmap

- [ ] **v0** — Repo scaffold, public engine with stub recipes, README, LICENSE, Dockerfile, .env.example.
- [ ] **v1 (in progress)** — Discovery + enrichment workers for Greater Toronto cannabis retail. Recipe library wired with private playbook override. Discord HITL surface. Gmail send. Open + reply tracking. Daily follow-up cron. First 50 emails to North York shops.
- [ ] **v2** — Autonomy thresholds per recipe. A/B subject-line tracker with statistical significance gates. Reply drafter (HITL). Per-prospect mock-up generation (auto-render exotic420budz.com with prospect's logo overlay).
- [ ] **v3** — Multi-product support: same engine drives outreach for non-cannabis Glitch productized SaaS. Pluggable discovery sources (LinkedIn Sales Navigator, Apollo). Inbound enrichment from website chat → lead.

---

## Why LangGraph

Outbound sales is a **state machine**, not a conversation:

```
discover → enrich → score → draft → [HITL gate] → send → observe → follow-up → memorize
```

LangGraph gives:
- **Durable checkpoints** — state survives restarts between HITL approvals (a draft can sit in the queue for hours before the operator sees it).
- **Per-node model selection** — Claude Sonnet for drafting, Gemini Flash for bulk classification (current-site detector runs on hundreds of pages), cheap fallback for "is this even a cannabis store" pre-filter.
- **Deterministic retries** — non-negotiable when sending live email under CASL.
- **One graph, many entry points** — the daily Cloud Scheduler kick, a Discord `/draft` slash command, and an inbound reply event all enter the same graph at different nodes.

CrewAI's role-framing pattern and AutoGen's conversation model are the wrong abstractions for a system that must produce reproducible, audit-able outbound mail whether a human or a scheduler triggered it.

---

## Contributing

Issues and PRs welcome. The public engine is open under BSL — implementation patterns, infrastructure, and the placeholder recipe surface are visible. Brand-specific copy and tuned thresholds are intentionally absent and live in the [private playbook](#private-playbook-pattern).

```bash
ruff check src/ tests/
mypy src/
pytest
```

---

## License

Business Source License 1.1 — see [LICENSE](LICENSE). Converts to Apache 2.0 on 2030-04-25. Production use is permitted except for offering the software as a competing hosted/embedded sales-agent product. For commercial licensing, contact support@glitchexecutor.com.

---

*Built by [Glitch Executor Labs](https://glitchexecutor.com) — AI-powered e-commerce operations.*

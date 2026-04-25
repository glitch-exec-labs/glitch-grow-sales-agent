"""Settings loaded from environment.

No per-prospect config lives here — that belongs in the `sales_agent.leads`
table. This module is for runtime knobs only: API keys, the sending mailbox,
the Discord channel, the daily outreach cap, the CASL footer.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Postgres ────────────────────────────────────────────────────────────
    postgres_rw_url: str

    # ── Discovery (Google Places API New, SA-impersonation auth) ───────────
    gcp_project_id: str = "capable-boulder-487806-j0"
    gcp_places_target_sa: str = (
        "glitch-vertex-ai@capable-boulder-487806-j0.iam.gserviceaccount.com"
    )
    discovery_center_lat: float = 43.7615
    discovery_center_lng: float = -79.4111
    discovery_radius_m: int = 8000

    # ── Email ──────────────────────────────────────────────────────────────
    gmail_oauth_client_id: str = ""
    gmail_oauth_client_secret: str = ""
    gmail_oauth_refresh_token: str = ""
    gmail_sender_email: str = ""
    gmail_sender_name: str = "Tejas"

    # ── CASL footer ────────────────────────────────────────────────────────
    casl_sender_name: str = "Glitch Executor Labs (Nuraveda)"
    casl_sender_address: str = "77 Huntley St, Toronto, ON"

    # ── Discord ────────────────────────────────────────────────────────────
    discord_bot_token: str = ""
    discord_guild_id: str = ""
    discord_approval_channel_id: str = ""
    discord_admin_user_ids: str = ""  # comma-separated

    # ── LLM providers ──────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # ── HubSpot CRM mirror ────────────────────────────────────────────────
    hubspot_pat: str = ""                          # Private App token
    hubspot_pipeline_name: str = "Glitch Budz"
    hubspot_sync_enabled: bool = False
    hubspot_portal_id: str = ""                    # optional, informational

    # ── Server ─────────────────────────────────────────────────────────────
    agent_run_token: str = ""
    outreach_daily_cap: int = 5

    # ── Optional ───────────────────────────────────────────────────────────
    sales_agent_dry_run: bool = False
    log_level: str = "INFO"

    @property
    def admin_user_id_list(self) -> list[int]:
        return [int(x.strip()) for x in self.discord_admin_user_ids.split(",") if x.strip()]


settings = Settings()  # type: ignore[call-arg]

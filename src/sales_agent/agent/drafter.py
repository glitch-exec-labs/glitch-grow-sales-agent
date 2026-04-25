"""Cold-email drafter — Gemini 2.5 Pro via Vertex AI.

Auth: same SA-impersonation pattern as the Places worker. ADC picks up
the box's attached Compute SA, which impersonates `glitch-vertex-ai@…`
so all Vertex calls are attributed to the operations SA.

Inputs per draft:
- The lead row (`Lead`).
- The recipe selected by `current_site_status` (private playbook
  recipes override stubs at import time).
- The brand fact sheet (private playbook → markdown loaded once).
- Optional `<prior_context>` summary of relevant past drafts/edits/
  replies. v1 leaves this empty; the recall layer plugs in once we
  have a few sends to learn from.

Output: `DraftResult` with subject_variant, subject, body, and token
telemetry. Structured JSON output is enforced via response_schema —
we don't have to coax the model with prose instructions.

The CASL footer is appended by the sender at send time — never by the
LLM — so footer + sender identity stay infra-controlled.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from google import genai
from google.auth import default as google_default
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from google.genai import types as genai_types

from sales_agent.agent.brand import get_brand_fact_sheet
from sales_agent.agent.prompts import get_system_prompt
from sales_agent.agent.recipes import RECIPES
from sales_agent.config import settings
from sales_agent.db.models import Lead

logger = logging.getLogger(__name__)

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


@dataclass
class DraftResult:
    subject_variant: str
    subject: str
    body: str
    model: str
    input_tokens: int
    output_tokens: int


# JSON schema enforced via Vertex's response_schema. No more prose-coaxing
# the model into well-formed JSON; the SDK guarantees the shape.
_DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject_variant": {"type": "string"},
        "subject":         {"type": "string"},
        "body":            {"type": "string"},
    },
    "required": ["subject_variant", "subject", "body"],
}


# ─── Prompt construction ─────────────────────────────────────────────────────


def render_user_prompt(lead: Lead, *, prior_context: str = "") -> str:
    platform = lead.pos_platform or lead.current_site_status or "custom"
    recipe = RECIPES.get(platform) or RECIPES.get("custom")
    if recipe is None:
        raise RuntimeError(
            "Recipe library missing 'custom' fallback — playbook misconfigured"
        )

    parts: list[str] = [
        "## Brand fact sheet — immutable, do not contradict",
        get_brand_fact_sheet(),
        "",
        "## Lead facts",
        f"- shop_name: {lead.business_name}",
        f"- neighbourhood: {lead.city or 'Toronto'}",
        f"- province: {lead.province}",
        f"- pos_platform: {platform}",
        f"- score: {lead.score}/100",
        f"- to_email: {lead.contact_email or '(unknown)'}",
        f"- website: {lead.website_url or '(none)'}",
        "",
        f"## Recipe (selected by pos_platform={platform})",
        f"- subject variants (pick ONE, do not invent): {list(recipe.subjects)}",
        f"- opener template: {recipe.opener!r}",
        "- body template (use as-is, only substitute {shop_name}):",
        recipe.body,
    ]

    if prior_context:
        parts += [
            "",
            "## Prior context (use to inform tone, do NOT paste verbatim)",
            prior_context,
        ]

    parts += [
        "",
        "## Output rules",
        "- pick `subject_variant` from the variants list above; do not invent a new subject",
        "- substitute {shop_name} with the actual shop name in the rendered subject + body",
        "- if the opener template is empty, omit the opener line entirely",
        "- keep the body ≤ 120 words",
        "- do not add prices, claims, or URLs that are not in the brand fact sheet or recipe template",
        "- the sender will append the CASL footer; do NOT include it",
    ]
    return "\n".join(parts)


# ─── Drafter ─────────────────────────────────────────────────────────────────


def _build_vertex_client() -> genai.Client:
    """Construct a google-genai Client wired for Vertex with SA impersonation."""
    source, _ = google_default(scopes=[CLOUD_PLATFORM_SCOPE])
    imp = ImpersonatedCredentials(
        source_credentials=source,
        target_principal=settings.gcp_target_sa,
        target_scopes=[CLOUD_PLATFORM_SCOPE],
        lifetime=3600,
    )
    return genai.Client(
        vertexai=True,
        project=settings.gcp_project_id,
        location=settings.gcp_vertex_region,
        credentials=imp,
    )


class Drafter:
    def __init__(
        self,
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.client = client or _build_vertex_client()
        self.model = model or settings.drafter_model
        self.max_tokens = max_tokens or settings.drafter_max_tokens

    async def draft(
        self, lead: Lead, *, prior_context: str = "",
    ) -> DraftResult:
        user_prompt = render_user_prompt(lead, prior_context=prior_context)
        system = get_system_prompt()

        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=self.max_tokens,
            response_mime_type="application/json",
            response_schema=_DRAFT_SCHEMA,
            temperature=0.3,
        )

        resp = await self.client.aio.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=config,
        )

        text = (resp.text or "").strip()
        if not text:
            raise RuntimeError(
                f"Drafter: empty response from {self.model}; "
                f"finish_reason={getattr(resp.candidates[0], 'finish_reason', '?') if resp.candidates else '?'}"
            )

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Drafter: model returned non-JSON output despite schema:\n{text[:500]}"
            ) from e

        for required in ("subject_variant", "subject", "body"):
            if required not in parsed:
                raise RuntimeError(
                    f"Drafter: missing field {required!r} in model output: {parsed!r}"
                )

        usage = resp.usage_metadata
        return DraftResult(
            subject_variant=str(parsed["subject_variant"]),
            subject=str(parsed["subject"]),
            body=str(parsed["body"]),
            model=self.model,
            input_tokens=int(getattr(usage, "prompt_token_count", 0) or 0),
            output_tokens=int(getattr(usage, "candidates_token_count", 0) or 0),
        )

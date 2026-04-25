"""Cold-email drafter — Claude Sonnet via the Anthropic SDK.

Inputs per draft:
- The lead row (`Lead`).
- The recipe selected by `current_site_status` (private playbook recipes
  override stubs at import time).
- The brand fact sheet (private playbook → markdown loaded once).
- Optional `<prior_context>` summary of relevant past drafts/edits/replies
  to ground the model in what worked / failed before. v1 leaves this
  empty; the recall layer plugs in once we have a few sends to learn from.

Output: parsed JSON `{subject_variant, subject, body, …telemetry}`.

The system prompt enforces tone + length + content constraints. The
model is instructed to choose a subject from the recipe's variants
(it MUST NOT invent new ones) and to substitute `{shop_name}` in the
opener template, then return the final rendered body.

We do not append the CASL footer here — the sender module appends it
at send time so the footer + sender identity are controlled by infra,
not the LLM.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic

from sales_agent.agent.brand import get_brand_fact_sheet
from sales_agent.agent.prompts import get_system_prompt
from sales_agent.agent.recipes import RECIPES
from sales_agent.config import settings
from sales_agent.db.models import Lead

logger = logging.getLogger(__name__)


@dataclass
class DraftResult:
    subject_variant: str
    subject: str
    body: str
    model: str
    input_tokens: int
    output_tokens: int


# ─── Prompt construction ─────────────────────────────────────────────────────


def render_user_prompt(lead: Lead, *, prior_context: str = "") -> str:
    site_status = lead.current_site_status or "custom"
    recipe = RECIPES.get(site_status, RECIPES.get("custom"))
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
        f"- current_site_status: {site_status}",
        f"- score: {lead.score}/100",
        f"- to_email: {lead.contact_email or '(unknown)'}",
        f"- website: {lead.website_url or '(none)'}",
        "",
        f"## Recipe (selected by current_site_status={site_status})",
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
        "## Output",
        "Return ONLY a JSON object, no prose, no code fences. Schema:",
        "{",
        '  "subject_variant": "<exact subject template you picked from the variants list>",',
        '  "subject":         "<rendered subject with substitutions>",',
        '  "body":            "<rendered body, opener + body, no signature, no CASL footer>"',
        "}",
        "",
        "Hard rules: substitute {shop_name} with the actual shop name; if the opener template "
        "is empty, omit the opener line entirely; keep the body ≤ 120 words; "
        "do not add prices, claims, or URLs that are not in the brand fact sheet or recipe template.",
    ]
    return "\n".join(parts)


# ─── JSON parsing ────────────────────────────────────────────────────────────


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


def parse_response_json(text: str) -> dict[str, Any]:
    """Tolerate markdown code fences around the JSON Claude returns."""
    cleaned = _FENCE_RE.sub("", text.strip())
    return json.loads(cleaned)


# ─── Drafter ─────────────────────────────────────────────────────────────────


class Drafter:
    def __init__(
        self,
        *,
        model: str | None = None,
        max_tokens: int = 1024,
        client: AsyncAnthropic | None = None,
    ) -> None:
        self.client = client or AsyncAnthropic()
        self.model = model or settings.drafter_model
        self.max_tokens = max_tokens

    async def draft(
        self, lead: Lead, *, prior_context: str = "",
    ) -> DraftResult:
        user_prompt = render_user_prompt(lead, prior_context=prior_context)
        system = get_system_prompt()

        msg = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Anthropic's TextBlock list — we ask for plain text JSON, expect one block.
        text_blocks = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        if not text_blocks:
            raise RuntimeError(f"Drafter: empty response from {self.model}")
        text = "\n".join(text_blocks).strip()

        try:
            parsed = parse_response_json(text)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Drafter: model returned non-JSON output:\n{text[:500]}"
            ) from e

        for required in ("subject_variant", "subject", "body"):
            if required not in parsed:
                raise RuntimeError(
                    f"Drafter: missing field {required!r} in model output: {parsed!r}"
                )

        return DraftResult(
            subject_variant=str(parsed["subject_variant"]),
            subject=str(parsed["subject"]),
            body=str(parsed["body"]),
            model=self.model,
            input_tokens=int(getattr(msg.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(msg.usage, "output_tokens", 0) or 0),
        )

"""Placeholder recipes — public, deliberately generic.

Real Glitch Budz copy lives in the private `glitch_grow_sales_playbook`
package and overrides this stub at import time (see `sales_agent.agent.recipes`).

Keys match `pos_platform` enum values from migrations/0003. If you're
running the public engine without the private package installed, the
agent will draft using these placeholders and the drafts won't sell.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    """A draft template keyed on `pos_platform`.

    Attributes:
        key:        The pos_platform enum value this recipe handles.
        subjects:   Subject-line variants (the tracker measures open rate per).
        opener:    The first sentence — the personalization slot. Empty
                    string means: omit the opener line, lead straight with
                    the body.
        body:      Recipe body excluding opener and signature.
    """

    key: str
    subjects: tuple[str, ...]
    opener: str
    body: str


_PLACEHOLDER_BODY = (
    "(placeholder body — install glitch_grow_sales_playbook to load real copy)"
)

# Generic stubs. Override these in glitch_grow_sales_playbook.recipes.
# Keys mirror PosPlatform: none / brochure / dutchie / blaze / tendypos / shopify / custom.
RECIPES: dict[str, Recipe] = {
    key: Recipe(
        key=key,
        subjects=("(placeholder subject)",),
        opener="(placeholder opener)" if key != "custom" else "",
        body=_PLACEHOLDER_BODY,
    )
    for key in ("none", "brochure", "dutchie", "blaze", "tendypos", "shopify", "custom")
}

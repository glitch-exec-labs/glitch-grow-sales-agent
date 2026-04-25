"""Placeholder recipes — public, deliberately generic.

Real Glitch Budz copy lives in the private `glitch_grow_sales_playbook`
package and overrides this stub at import time (see `sales_agent.agent.recipes`).

If you're running the public engine without the private package installed,
the agent will draft using these placeholders. The drafts will compile and
send, but they won't sell anything — that's intentional. The operator's edge
is the calibrated copy in the private package.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recipe:
    """A draft template keyed on `current_site_status`.

    Attributes:
        key:        The `current_site_status` enum value this recipe handles.
        subjects:   Subject-line variants (the tracker will measure open rate per).
        opener:    The first sentence of the body — the personalization slot.
        body:      Recipe body excluding opener and signature.
    """

    key: str
    subjects: tuple[str, ...]
    opener: str
    body: str


# Generic stubs. Override these in glitch_grow_sales_playbook.recipes.
RECIPES: dict[str, Recipe] = {
    "none": Recipe(
        key="none",
        subjects=("(placeholder subject)",),
        opener="(placeholder opener — install the private playbook package)",
        body="(placeholder body)",
    ),
    "linktree": Recipe(
        key="linktree",
        subjects=("(placeholder subject)",),
        opener="(placeholder opener — install the private playbook package)",
        body="(placeholder body)",
    ),
    "builder": Recipe(
        key="builder",
        subjects=("(placeholder subject)",),
        opener="(placeholder opener — install the private playbook package)",
        body="(placeholder body)",
    ),
    "lightspeed": Recipe(
        key="lightspeed",
        subjects=("(placeholder subject)",),
        opener="(placeholder opener — install the private playbook package)",
        body="(placeholder body)",
    ),
    "custom": Recipe(
        key="custom",
        subjects=("(placeholder subject)",),
        opener="",  # custom sites get no personalization line; lead with price
        body="(placeholder body)",
    ),
}

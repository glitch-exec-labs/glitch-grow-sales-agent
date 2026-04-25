"""Recipe resolution layer.

At import time, try to load the calibrated recipes from the private
`glitch_grow_sales_playbook` package. If the package is not installed
(public-only dev clone, contributor PR, CI without secret access), fall
back to the stub recipes shipped in this repo.

Same pattern as `glitch-grow-ads-agent-private` — keeps the public engine
runnable while the operator's edge stays out of the public repo.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from glitch_grow_sales_playbook.recipes import RECIPES  # type: ignore[import-not-found]

    logger.info("recipes: loaded from glitch_grow_sales_playbook (private)")
except ImportError:
    from sales_agent.agent.recipes_stub import RECIPES

    logger.warning(
        "recipes: glitch_grow_sales_playbook not importable — using public stubs. "
        "Drafts will compile but won't be useful for actual selling."
    )

__all__ = ["RECIPES"]

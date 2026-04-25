"""Classify a shop's website into the `current_site_status` enum.

Pattern-matching is fully deterministic and free — no LLM call. Each
recipe in the playbook is keyed on this enum, so the classifier's job
is to land on one of:

    none        — HTTP error, blank page, no website at all
    linktree    — Linktree, Bio.link, Beacons, lnk.bio, similar aggregators
    builder     — Wix, Squarespace, Weebly, GoDaddy Sites, Carrd, WordPress.com
    lightspeed  — Lightspeed Cannabis / Lightspeed eCom signatures
    custom      — anything else (hand-coded, agency build, headless)

The classifier is intentionally conservative: when in doubt, returns
`custom` so the recipe library defaults to the price-led, no-personalization
opener instead of accidentally telling a shop their site looks like a
template buy.
"""

from __future__ import annotations

import logging
from typing import Literal
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

SiteStatus = Literal["none", "linktree", "builder", "lightspeed", "custom"]


# Hosts that are themselves link-aggregator products. If the website_url
# is on one of these, the shop has *no real site* — they live in someone
# else's bio-link page.
LINKTREE_HOSTS: frozenset[str] = frozenset({
    "linktr.ee", "lnk.bio", "beacons.ai", "bio.link", "snipfeed.co",
    "linkin.bio", "stan.store", "withkoji.com", "campsite.bio",
})

# Substrings in HTML that indicate a hosted SaaS website builder.
BUILDER_SIGNATURES: tuple[str, ...] = (
    "wixstatic.com", "wix.com/website", "_wix_",
    "squarespace.com", "static1.squarespace", "squarespace-cdn",
    "weebly.com", "/weebly/",
    "godaddy.com/sites", "godaddysites.com",
    "carrd.co",
    "wordpress.com",
    # Shopify shouldn't really appear (cannabis-rejected), but if it does
    # treat as builder — same conversation we'd have with a Wix shop.
    "myshopify.com", "cdn.shopify.com", "/cdn/shop/",
)

# Lightspeed Cannabis / Lightspeed eCom signatures.
LIGHTSPEED_SIGNATURES: tuple[str, ...] = (
    "lightspeedhq.com",
    "lightspeed-ecom",
    "cdn.lightspeed",
    "ecom-spazi",       # legacy Lightspeed eCom CDN
    "lightspeed-cannabis",
    "shoplightspeed.com",
)

# Linktree-style references that may appear inside an otherwise-custom site
# (e.g., a shop with their own homepage that links out to a Linktree). If
# these are present *and no other signature matches*, classify as linktree
# because the shop is treating Linktree as their primary surface.
LINKTREE_INPAGE: tuple[str, ...] = ("linktr.ee", "linktree.com", "lnk.bio")


def _host_of(url: str) -> str | None:
    try:
        host = urlparse(url if "://" in url else f"https://{url}").hostname
    except (ValueError, TypeError):
        return None
    if not host:
        return None
    return host.lower().removeprefix("www.")


def classify_url_only(url: str | None) -> SiteStatus | None:
    """Decide based on URL host alone. Returns None if a fetch is needed."""
    if not url:
        return "none"
    host = _host_of(url)
    if not host:
        return "none"
    # The website_url IS a Linktree-style aggregator.
    for h in LINKTREE_HOSTS:
        if host == h or host.endswith("." + h):
            return "linktree"
    return None  # need to fetch the page to decide


def classify_html(html: str) -> SiteStatus:
    """Classify by signatures inside fetched HTML."""
    if not html:
        return "none"
    if len(html) < 200:
        # Pages this short are usually blank-template, redirect stubs, or
        # error pages. Treat as no real site.
        return "none"
    lower = html.lower()
    for sig in LIGHTSPEED_SIGNATURES:
        if sig in lower:
            return "lightspeed"
    for sig in BUILDER_SIGNATURES:
        if sig in lower:
            return "builder"
    for sig in LINKTREE_INPAGE:
        if sig in lower:
            return "linktree"
    return "custom"


async def detect(
    url: str | None,
    client: httpx.AsyncClient,
    *,
    timeout: float = 15.0,
) -> SiteStatus:
    """Full classification: URL check first, then fetch + HTML check.

    Returns `none` on network errors, timeouts, 4xx/5xx, or empty pages —
    these are operationally indistinguishable from "no real site" for
    the drafter's purposes.
    """
    if not url:
        return "none"
    by_url = classify_url_only(url)
    if by_url is not None and by_url != "custom":
        return by_url
    try:
        resp = await client.get(url, follow_redirects=True, timeout=timeout)
    except (httpx.TransportError, httpx.TimeoutException) as e:
        logger.debug("site_detector: fetch failed for %s: %s", url, e)
        return "none"
    if resp.status_code >= 400:
        return "none"
    return classify_html(resp.text)

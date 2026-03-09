"""URL normalization utilities for incremental pipeline."""
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


# Tracking/noise params to strip
NOISE_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "mc_cid", "mc_eid", "srsltid",
    "variant", "_pos", "_sid", "_ss", "_fid", "_v",
}

# URL path segments to blacklist from crawling
BLACKLIST_PATHS = {
    "/cart", "/checkout", "/login", "/register", "/account",
    "/search", "/wishlist", "/compare",
}


def normalize_url(url: str) -> str:
    """Normalize URL: strip tracking params, fragments, trailing slash, lowercase host."""
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove www prefix for consistency
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Clean path: remove trailing slash (except root)
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

    # Strip noise query params
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean_params = {k: v for k, v in params.items() if k.lower() not in NOISE_PARAMS}
        query = urlencode(clean_params, doseq=True) if clean_params else ""
    else:
        query = ""

    # Remove fragment
    return urlunparse((scheme, netloc, path, "", query, ""))


def urls_are_same(url_a: str, url_b: str) -> bool:
    """Check if two URLs point to the same canonical page."""
    return normalize_url(url_a) == normalize_url(url_b)


def is_blacklisted_url(url: str) -> bool:
    """Check if URL should be skipped during crawling."""
    parsed = urlparse(url)
    path = parsed.path.lower()

    # Check blacklisted paths
    for bp in BLACKLIST_PATHS:
        if path.startswith(bp):
            return True

    # Check file extensions
    skip_exts = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".gif", ".zip", ".css", ".js", ".svg", ".ico"}
    if any(path.endswith(ext) for ext in skip_exts):
        return True

    return False

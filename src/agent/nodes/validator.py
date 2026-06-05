"""Node 3 — Validator. Filters 404s and scores results for scam signals."""
import re
import httpx
from urllib.parse import urlparse

from src.agent.state import AgentState, RawResult

# Known scam / low-quality TLDs and domain patterns
_SCAM_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".click", ".top"}

_SCAM_KEYWORDS = [
    "earn-money-fast", "get-rich", "work-from-home-guaranteed",
    "unlimited-income", "click-here-to-win", "free-iphone",
    "survey-rewards", "prize-winner", "congratulations-you-won",
    "crypto-profit", "binary-options", "forex-signals-free",
]

_SCAM_DOMAIN_PATTERNS = [
    r"\d{4,}",          # domains with long number sequences
    r"(.)\1{4,}",       # repeated characters (aaaaa.com)
    r"free.?money",
    r"win.?prize",
    r"earn.?online",
    r"job.?guarantee",
]

# Trusted domains get an instant pass — skip HTTP check and scam scoring
_TRUSTED_DOMAINS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "wellfound.com",
    "remoteok.com", "weworkremotely.com",
    "rtings.com", "wirecutter.com", "tomsguide.com", "techradar.com",
    "reddit.com", "cnet.com", "theverge.com", "tomshardware.com",
    "wikipedia.org", "github.com", "stackoverflow.com",
    "deeplearning.ai", "arxiv.org", "medium.com",
}

_SCAM_THRESHOLD = 3   # reject if scam score >= this
_HTTP_TIMEOUT   = 5.0 # seconds


def _root_domain(url: str) -> str:
    host = urlparse(url).hostname or ""
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def _scam_score(url: str, title: str, snippet: str) -> tuple[int, list[str]]:
    """Returns (score, reasons). Score >= _SCAM_THRESHOLD → reject."""
    score = 0
    reasons: list[str] = []

    parsed = urlparse(url)
    host = parsed.hostname or ""
    tld = "." + host.rsplit(".", 1)[-1] if "." in host else ""
    combined = f"{url} {title} {snippet}".lower()

    if tld in _SCAM_TLDS:
        score += 3
        reasons.append(f"suspicious TLD '{tld}'")

    for kw in _SCAM_KEYWORDS:
        if kw in combined:
            score += 2
            reasons.append(f"scam keyword '{kw}'")
            break  # one hit is enough

    for pat in _SCAM_DOMAIN_PATTERNS:
        if re.search(pat, host, re.I):
            score += 2
            reasons.append(f"domain pattern '{pat}'")
            break

    if len(host.split(".")[0]) > 30:
        score += 1
        reasons.append("unusually long subdomain")

    if not parsed.scheme.startswith("http"):
        score += 3
        reasons.append("non-HTTP scheme")

    return score, reasons


def _is_reachable(url: str) -> bool:
    """HEAD request — returns False on 4xx/5xx or connection error."""
    try:
        r = httpx.head(url, timeout=_HTTP_TIMEOUT, follow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False


def validate_results(state: AgentState) -> dict:
    raw = state["raw_results"]
    valid: list[RawResult] = []

    for result in raw:
        url   = result["url"]
        title = result["title"]
        snip  = result["snippet"]
        domain = _root_domain(url)

        # Trusted domains: skip heavy checks
        if domain in _TRUSTED_DOMAINS:
            valid.append(result)
            continue

        # Scam scoring
        score, reasons = _scam_score(url, title, snip)
        if score >= _SCAM_THRESHOLD:
            print(f"[Validator] REJECTED (scam score {score}) {url} — {reasons}")
            continue

        # 404 / reachability check
        if not _is_reachable(url):
            print(f"[Validator] REJECTED (unreachable) {url}")
            continue

        valid.append(result)

    print(f"[Validator] {len(valid)}/{len(raw)} results passed")
    return {"valid_results": valid}

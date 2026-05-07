import re
import requests
import xml.etree.ElementTree as ET
from datetime import date, datetime
from flask import current_app

ATOM_NS = "http://www.w3.org/2005/Atom"

# All workloads prefixed with "Copilot in" to make clear every feature is a Copilot capability.
# Platform-level entries (Studio, Admin, Security) keep their own names.
WORKLOAD_MAP = {
    # Platform / standalone — keep as-is
    "copilot studio":           "Copilot Studio",
    "microsoft 365 copilot":    "Microsoft 365 Copilot",
    "copilot extensibility":    "Copilot Extensibility",
    "microsoft 365 admin":      "Copilot Admin & Governance",
    "microsoft purview":        "Copilot Security & Compliance",
    "purview":                  "Copilot Security & Compliance",
    "microsoft graph":          "Copilot Platform (Graph)",
    # Host-app integrations — "Copilot in X"
    "microsoft teams":          "Copilot in Teams",
    "teams":                    "Copilot in Teams",
    "outlook":                  "Copilot in Outlook",
    "word":                     "Copilot in Word",
    "excel":                    "Copilot in Excel",
    "powerpoint":               "Copilot in PowerPoint",
    "onenote":                  "Copilot in OneNote",
    "sharepoint":               "Copilot in SharePoint",
    "onedrive":                 "Copilot in OneDrive",
    "loop":                     "Copilot in Loop",
    "whiteboard":               "Copilot in Whiteboard",
    "planner":                  "Copilot in Planner",
    "forms":                    "Copilot in Forms",
    "stream":                   "Copilot in Stream",
    "viva insights":            "Copilot in Viva Insights",
    "viva engage":              "Copilot in Viva Engage",
    "viva learning":            "Copilot in Viva Learning",
    "viva goals":               "Copilot in Viva Goals",
    "viva connections":         "Copilot in Viva Connections",
    "viva":                     "Copilot in Viva",
    "power automate":           "Copilot in Power Automate",
    "power apps":               "Copilot in Power Apps",
    "power platform":           "Copilot in Power Platform",
    "project":                  "Copilot in Project",
    "yammer":                   "Copilot in Yammer",
    "microsoft search":         "Copilot in Microsoft Search",
    "microsoft entra":          "Copilot in Entra",
    "microsoft 365 apps":       "Copilot in M365 Apps",
}

PLATFORM_KEYWORDS = {
    "web", "desktop", "mobile", "ios", "android", "mac",
    "windows", "teams rooms", "tablet",
}

STATUS_MAP = {
    "rolling out": "Rolling Out",
    "launched": "GA",
    "in development": "In Development",
}

PHASE_PRIORITY = ["frontier", "preview", "targeted release", "general availability"]
PHASE_DISPLAY = {
    "frontier": "Frontier",
    "preview": "Preview",
    "targeted release": "Targeted Release",
    "general availability": "General Availability",
}


def fetch_roadmap_features():
    url = current_app.config["ROADMAP_RSS_URL"]
    timeout = current_app.config.get("ROADMAP_FETCH_TIMEOUT", 30)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CopilotRoadmapTracker/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return _parse_rss(resp.content)


def _parse_rss(xml_bytes):
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("No <channel> found in RSS feed")

    features = []
    for item in channel.findall("item"):
        parsed = _parse_item(item)
        if parsed and _is_copilot(parsed):
            features.append(parsed)
    return features


def _is_copilot(f):
    """
    Only include features that Microsoft has explicitly tagged as a Copilot feature.
    Relying solely on category tags avoids picking up general M365 features that
    happen to mention 'Copilot' in their description.
    """
    cats = [c.lower() for c in f.get("_categories", [])]
    # Microsoft explicitly categorises Copilot features with one of these tags
    return any("copilot" in c for c in cats)


def _parse_item(item):
    guid = (item.findtext("guid") or "").strip()
    title = (item.findtext("title") or "").strip()
    link = (item.findtext("link") or "").strip()
    description = _clean_html(item.findtext("description") or "")
    pub_date_str = (item.findtext("pubDate") or "").strip()

    updated_el = item.find(f"{{{ATOM_NS}}}updated")
    updated_str = (updated_el.text or "").strip() if updated_el is not None else ""

    categories = [c.text.strip() for c in item.findall("category") if c.text]

    workload = _extract_workload(title, categories)
    release_status = _extract_status(categories)
    release_phase = _extract_phase(categories)
    ga_estimate = _extract_ga_date(description, release_status)
    platforms = _extract_platforms(categories)
    confidence = _derive_confidence(release_status, release_phase)
    business_readiness = _derive_readiness(release_status, release_phase)

    return {
        "feature_id": f"ms-{guid}" if guid else None,
        "name": title,
        "workload": workload,
        "description": description,
        "release_status": release_status,
        "release_phase": release_phase,
        "ga_estimate": ga_estimate,
        "confidence_level": confidence,
        "business_readiness": business_readiness,
        "platforms": ", ".join(platforms),
        "roadmap_link": link,
        "published_date": _parse_rss_date(pub_date_str),
        "last_roadmap_update": _parse_iso_date(updated_str),
        "source": "roadmap",
        "is_custom": False,
        "_categories": categories,
    }


def _extract_workload(title, categories):
    # Title prefix (e.g. "Microsoft Teams: AI notes...") is the most reliable signal
    if ":" in title:
        product_part = title.split(":")[0].lower().strip()
        for key, val in WORKLOAD_MAP.items():
            if key in product_part:
                return val
    # Fall back to explicit category tags
    for cat in categories:
        cat_lower = cat.lower()
        for key, val in WORKLOAD_MAP.items():
            if key in cat_lower:
                return val
    # Everything in this app is a Copilot feature; unknown host = platform-level
    return "Microsoft 365 Copilot"


def _extract_status(categories):
    cats_lower = [c.lower() for c in categories]
    for key, val in STATUS_MAP.items():
        if any(key in c for c in cats_lower):
            return val
    return "In Development"


def _extract_phase(categories):
    cats_lower = [c.lower() for c in categories]
    for phase_key in PHASE_PRIORITY:
        if any(phase_key in c for c in cats_lower):
            return PHASE_DISPLAY[phase_key]
    return "General Availability"


def _extract_platforms(categories):
    result = []
    for cat in categories:
        cat_lower = cat.lower()
        for pk in PLATFORM_KEYWORDS:
            if pk in cat_lower and cat not in result:
                result.append(cat)
                break
    return result


def _extract_ga_date(description, release_status=""):
    """
    Extract a future-facing GA estimate from the feature description.

    Two-pass strategy:
      Pass 1 — search for a date that appears directly after GA-specific language
               ("general availability", "rolling out", "available to all" etc.).
               This avoids picking up preview or targeted-release dates that often
               appear earlier in the same description.
      Pass 2 — fall back to the first recognisable date anywhere in the text.

    After extraction: if the feature is still In Development and the extracted
    date is in the past, return None — a stale estimate is worse than no estimate.
    """
    # Pass 1: date right after GA-context keyword
    GA_CONTEXT = (
        r"(?:general\s+availability|rolling\s+out(?:\s+to\s+(?:GA|general))?|"
        r"available\s+(?:to\s+all|worldwide|generally)|"
        r"GA\s*(?:date\s*)?(?:[:\-–]|\s+in\s+|\s+by\s+)|"
        r"launch(?:es|ing|ed)?(?:\s+in)?)\s*(?:[:\-–])?\s*"
    )
    result = _search_date(GA_CONTEXT + _DATE_FRAGMENT(), description) or \
             _search_date(_DATE_FRAGMENT(), description)

    if result and release_status == "In Development":
        approx = _approximate_date(result)
        if approx and approx < date.today():
            # Stale — Microsoft's description hasn't been updated after a slip
            return None

    return result


def _DATE_FRAGMENT():
    MONTHS = (
        "january|february|march|april|may|june|"
        "july|august|september|october|november|december|"
        "jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec"
    )
    YEAR = r"202[4-9]|203[0-9]"
    return (
        r"(?:"
        r"(?:" + MONTHS + r")\.?\s+(?:" + YEAR + r")"    # June 2026 / Jun 2026
        r"|Q[1-4]\s*(?:CY\s*)?(?:" + YEAR + r")"        # Q2 2026 / Q2 CY2026
        r"|CY\s*(?:" + YEAR + r")"                       # CY2026
        r"|H[12]\s*(?:" + YEAR + r")"                    # H1 2026
        r"|(?:first|second)\s+half\s+(?:of\s+)?(?:" + YEAR + r")"  # first half of 2026
        r"|(?:early|mid|late)\s+(?:" + YEAR + r")"      # early 2026
        r")"
    )


def _search_date(pattern, text):
    """Run pattern against text and normalise the matched date string."""
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(0).strip()

    MONTHS_FULL = ["january","february","march","april","may","june",
                   "july","august","september","october","november","december"]
    MONTHS_ABBR = ["jan","feb","mar","apr","may","jun",
                   "jul","aug","sep","oct","nov","dec"]
    YEAR_PAT = r"(202[4-9]|203[0-9])"
    raw_lower = raw.lower()

    # Month YYYY
    mp = r"\b(" + "|".join(MONTHS_FULL + MONTHS_ABBR) + r")\.?\s+" + YEAR_PAT
    mm = re.search(mp, raw_lower)
    if mm:
        name = mm.group(1).rstrip(".")
        if len(name) == 3 and name in MONTHS_ABBR:
            name = MONTHS_FULL[MONTHS_ABBR.index(name)]
        return f"{name.capitalize()} {mm.group(2)}"

    mm = re.search(r"\bQ([1-4])\s*(?:CY\s*)?" + YEAR_PAT, raw, re.IGNORECASE)
    if mm:
        return f"Q{mm.group(1)} {mm.group(2)}"

    mm = re.search(r"\bCY\s?" + YEAR_PAT, raw, re.IGNORECASE)
    if mm:
        return f"CY {mm.group(1)}"

    mm = re.search(r"\bH([12])\s*" + YEAR_PAT, raw, re.IGNORECASE)
    if mm:
        return f"H{mm.group(1)} {mm.group(2)}"

    mm = re.search(r"\b(first|second)\s+half\s+(?:of\s+)?" + YEAR_PAT, raw_lower)
    if mm:
        return f"{'H1' if mm.group(1) == 'first' else 'H2'} {mm.group(2)}"

    mm = re.search(r"\b(early|mid|late)\s+" + YEAR_PAT, raw_lower)
    if mm:
        return f"{mm.group(1).capitalize()} {mm.group(2)}"

    return None


def _approximate_date(estimate):
    """
    Convert a ga_estimate string to an approximate END date of the period.
    We use the end (not start) so that "H1 2026" isn't considered past
    until July 2026, not March 2026.
    """
    if not estimate:
        return None
    import calendar
    MONTHS_FULL = ["january","february","march","april","may","june",
                   "july","august","september","october","november","december"]
    est_lower = estimate.lower()
    year_m = re.search(r"(202\d|203\d)", estimate)
    if not year_m:
        return None
    year = int(year_m.group(1))

    # Quarter → last month of that quarter
    q_m = re.search(r"Q([1-4])", estimate, re.IGNORECASE)
    if q_m:
        end_month = int(q_m.group(1)) * 3          # Q1→3, Q2→6, Q3→9, Q4→12
        last_day = calendar.monthrange(year, end_month)[1]
        return date(year, end_month, last_day)

    # Half-year → last day of H1 (June 30) or H2 (Dec 31)
    h_m = re.search(r"H([12])", estimate, re.IGNORECASE)
    if h_m:
        end_month = 6 if h_m.group(1) == "1" else 12
        last_day = calendar.monthrange(year, end_month)[1]
        return date(year, end_month, last_day)

    # Named month → last day of that month
    for i, name in enumerate(MONTHS_FULL, start=1):
        if name in est_lower:
            return date(year, i, calendar.monthrange(year, i)[1])

    # CY / Early / Mid / Late / bare year → end of year
    if "early" in est_lower:
        return date(year, 4, 30)   # end of April is safe for "early"
    if "mid" in est_lower:
        return date(year, 8, 31)
    # late, CY, bare year — end of year
    return date(year, 12, 31)


def _derive_confidence(release_status, release_phase):
    if release_status in ("GA", "Rolling Out"):
        return "High"
    if release_phase == "Frontier":
        return "Low"
    if release_phase in ("Preview", "Targeted Release"):
        return "Medium"
    if release_status == "In Development" and release_phase == "General Availability":
        return "Medium"
    return "Low"


def _derive_readiness(release_status, release_phase):
    if release_status == "GA":
        return "Safe to Promote"
    if release_status == "Rolling Out":
        if release_phase in ("General Availability", "Targeted Release"):
            return "Safe to Promote"
        return "Pilot Only"
    if release_phase == "Frontier":
        return "Do Not Commit"
    if release_status == "In Development":
        return "Pilot Only"
    return "Pilot Only"


def _parse_rss_date(date_str):
    if not date_str:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None


def _parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clean_html(text):
    return re.sub(r"<[^>]+>", "", text).strip()

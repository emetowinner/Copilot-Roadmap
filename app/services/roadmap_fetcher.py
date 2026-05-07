import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
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
    ga_estimate = _extract_ga_date(description)
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


def _extract_ga_date(description):
    """
    Extract a GA/rollout date estimate from the feature description.
    Microsoft uses several formats across roadmap entries; we try each in order
    of specificity (most precise first).
    """
    MONTHS = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ]
    MONTH_ABBR = [
        "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec",
    ]
    YEAR = r"(202[4-9]|203[0-9])"
    desc_lower = description.lower()

    # "June 2026" / "Jun 2026"
    month_pat = r"\b(" + "|".join(MONTHS + MONTH_ABBR) + r")\.?\s+" + YEAR + r"\b"
    m = re.search(month_pat, desc_lower)
    if m:
        raw = m.group(1).rstrip(".")
        # normalise abbreviations to full month name
        if len(raw) == 3:
            idx = MONTH_ABBR.index(raw)
            raw = MONTHS[idx]
        return f"{raw.capitalize()} {m.group(2)}"

    # "Q2 2026" / "Q2 CY2026" / "Q2CY2026"
    m = re.search(r"\bQ([1-4])\s*(?:CY\s*)?" + YEAR + r"\b", description, re.IGNORECASE)
    if m:
        return f"Q{m.group(1)} {m.group(2)}"

    # "CY2026" / "CY 2026"
    m = re.search(r"\bCY\s?" + YEAR + r"\b", description, re.IGNORECASE)
    if m:
        return f"CY {m.group(1)}"

    # "H1 2026" / "H2 2026"
    m = re.search(r"\bH([12])\s*" + YEAR + r"\b", description, re.IGNORECASE)
    if m:
        return f"H{m.group(1)} {m.group(2)}"

    # "first half of 2026" / "second half of 2026"
    m = re.search(r"\b(first|second)\s+half\s+(?:of\s+)?" + YEAR + r"\b", desc_lower)
    if m:
        half = "H1" if m.group(1) == "first" else "H2"
        return f"{half} {m.group(2)}"

    # "early 2026" / "mid 2026" / "late 2026"
    m = re.search(r"\b(early|mid|late)\s+" + YEAR + r"\b", desc_lower)
    if m:
        label_map = {"early": "Early", "mid": "Mid", "late": "Late"}
        return f"{label_map[m.group(1)]} {m.group(2)}"

    # Bare year as last resort — only if year appears near rollout language
    if re.search(r"\b(roll(?:ing)?\s*out|availa(?:ble|bility)|general availability|launch)\b", desc_lower):
        m = re.search(YEAR, description)
        if m:
            return m.group(1)

    return None


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

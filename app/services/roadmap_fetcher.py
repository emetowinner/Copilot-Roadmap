import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import current_app

ATOM_NS = "http://www.w3.org/2005/Atom"

WORKLOAD_MAP = {
    "copilot studio": "Copilot Studio",
    "microsoft 365 copilot": "Microsoft 365 Copilot",
    "microsoft teams": "Teams",
    "outlook": "Outlook",
    "word": "Word",
    "excel": "Excel",
    "powerpoint": "PowerPoint",
    "onenote": "OneNote",
    "sharepoint": "SharePoint",
    "onedrive": "OneDrive",
    "viva insights": "Viva Insights",
    "viva engage": "Viva Engage",
    "viva learning": "Viva Learning",
    "viva goals": "Viva Goals",
    "viva connections": "Viva Connections",
    "viva": "Viva",
    "purview": "Purview",
    "power platform": "Power Platform",
    "power automate": "Power Automate",
    "power apps": "Power Apps",
    "microsoft 365 admin": "M365 Admin",
    "microsoft 365 apps": "M365 Apps",
    "loop": "Loop",
    "whiteboard": "Whiteboard",
    "planner": "Planner",
    "project": "Project",
    "forms": "Forms",
    "stream": "Stream",
    "yammer": "Yammer",
    "microsoft search": "Microsoft Search",
    "microsoft graph": "Microsoft Graph",
    "microsoft entra": "Entra",
    "teams": "Teams",
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
    cats = [c.lower() for c in f.get("_categories", [])]
    if any("copilot" in c for c in cats):
        return True
    if "copilot" in (f.get("name") or "").lower():
        return True
    return False


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
    if ":" in title:
        product_part = title.split(":")[0].lower().strip()
        for key, val in WORKLOAD_MAP.items():
            if key in product_part:
                return val
        return title.split(":")[0].strip()
    for cat in categories:
        cat_lower = cat.lower()
        for key, val in WORKLOAD_MAP.items():
            if key in cat_lower:
                return val
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
    MONTHS = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ]
    desc_lower = description.lower()
    month_pat = r"\b(" + "|".join(MONTHS) + r")\s+(202[4-9]|203[0-9])\b"
    matches = re.findall(month_pat, desc_lower)
    if matches:
        return f"{matches[0][0].capitalize()} {matches[0][1]}"
    q_pat = r"\b[Qq]([1-4])\s*(?:CY)?\s*(202[4-9]|203[0-9])\b"
    q_matches = re.findall(q_pat, description)
    if q_matches:
        return f"Q{q_matches[0][0]} {q_matches[0][1]}"
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

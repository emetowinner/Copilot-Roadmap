from datetime import datetime

TRACKED_FIELDS = [
    "name",
    "workload",
    "release_status",
    "release_phase",
    "ga_estimate",
    "confidence_level",
    "business_readiness",
    "platforms",
    "roadmap_link",
]

FIELD_LABELS = {
    "name": "Feature Name",
    "workload": "Workload",
    "release_status": "Release Status",
    "release_phase": "Release Phase",
    "ga_estimate": "GA Estimate",
    "confidence_level": "Confidence Level",
    "business_readiness": "Business Readiness",
    "platforms": "Platforms",
    "roadmap_link": "Roadmap Link",
}


def compute_diff(existing_features, fetched_features):
    existing_map = {
        f.feature_id: f
        for f in existing_features
        if f.feature_id and f.feature_id.startswith("ms-")
    }
    fetched_map = {
        f["feature_id"]: f
        for f in fetched_features
        if f.get("feature_id")
    }

    added, modified, removed, unchanged = [], [], [], []

    for fid, fetched in fetched_map.items():
        if fid not in existing_map:
            added.append({"feature_id": fid, "feature": fetched})
        else:
            existing = existing_map[fid]
            changes = _field_changes(existing, fetched)
            if changes:
                modified.append({
                    "feature_id": fid,
                    "feature_name": fetched.get("name", existing.name),
                    "existing": existing,
                    "fetched": fetched,
                    "changes": changes,
                })
            else:
                unchanged.append({
                    "feature_id": fid,
                    "feature_name": existing.name,
                    "workload": existing.workload,
                    "release_status": existing.release_status,
                    "release_phase": existing.release_phase,
                    "ga_estimate": existing.ga_estimate,
                    "business_readiness": existing.business_readiness,
                })

    for fid, existing in existing_map.items():
        if fid not in fetched_map and not existing.is_custom:
            removed.append({
                "feature_id": fid,
                "feature_name": existing.name,
                "workload": existing.workload,
                "release_status": existing.release_status,
            })

    return {
        "added": added,
        "modified": modified,
        "removed": removed,
        "unchanged": unchanged,
        "total_changes": len(added) + len(modified) + len(removed),
        "detected_at": datetime.utcnow().isoformat(),
    }


def _field_changes(existing, fetched):
    changes = []
    for field in TRACKED_FIELDS:
        old_val = str(getattr(existing, field) or "").strip()
        new_val = str(fetched.get(field) or "").strip()
        if old_val != new_val:
            changes.append({
                "field": field,
                "label": FIELD_LABELS.get(field, field.replace("_", " ").title()),
                "old_value": old_val,
                "new_value": new_val,
            })
    return changes


def serialize_diff(diff):
    result = {
        "added": [],
        "modified": [],
        "removed": diff["removed"],
        "unchanged": diff["unchanged"],
        "total_changes": diff["total_changes"],
        "detected_at": diff["detected_at"],
    }

    for item in diff["added"]:
        f = item["feature"]
        result["added"].append({
            "feature_id": item["feature_id"],
            "name": f.get("name", ""),
            "workload": f.get("workload", ""),
            "release_status": f.get("release_status", ""),
            "release_phase": f.get("release_phase", ""),
            "ga_estimate": f.get("ga_estimate") or "",
            "confidence_level": f.get("confidence_level", ""),
            "business_readiness": f.get("business_readiness", ""),
        })

    for item in diff["modified"]:
        result["modified"].append({
            "feature_id": item["feature_id"],
            "feature_name": item["feature_name"],
            "workload": item["fetched"].get("workload", ""),
            "changes": item["changes"],
        })

    return result

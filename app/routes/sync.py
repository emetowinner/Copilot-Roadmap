from datetime import datetime

from flask import Blueprint, jsonify, request

from app import db
from app.models import ChangeLog, Feature, SyncLog
from app.services.diff_engine import compute_diff, serialize_diff
from app.services.roadmap_fetcher import fetch_roadmap_features

sync_bp = Blueprint("sync", __name__)


@sync_bp.route("/refresh", methods=["POST"])
def refresh():
    sync_log = SyncLog(sync_type="refresh", started_at=datetime.utcnow(), status="running")
    db.session.add(sync_log)
    db.session.commit()

    try:
        fetched = fetch_roadmap_features()
        existing = Feature.query.filter_by(is_deleted=False, is_custom=False).all()
        diff = compute_diff(existing, fetched)

        sync_log.items_fetched = len(fetched)
        sync_log.items_added = len(diff["added"])
        sync_log.items_modified = len(diff["modified"])
        sync_log.items_removed = len(diff["removed"])
        db.session.commit()

        if diff["total_changes"] == 0:
            sync_log.status = "success"
            sync_log.completed_at = datetime.utcnow()
            db.session.commit()
            return jsonify({
                "status": "no_changes",
                "message": f"Up to date. {len(fetched)} Copilot features checked — no changes detected.",
                "fetched": len(fetched),
            })

        return jsonify({
            "status": "changes_detected",
            "diff": serialize_diff(diff),
            "sync_log_id": sync_log.id,
            "fetched": len(fetched),
        })

    except Exception as exc:
        sync_log.status = "failed"
        sync_log.error_message = str(exc)
        sync_log.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"status": "error", "message": str(exc)}), 500


@sync_bp.route("/apply", methods=["POST"])
def apply_changes():
    data = request.get_json()
    sync_log_id = data.get("sync_log_id")
    to_add = data.get("added", [])          # list of feature_ids
    to_modify = data.get("modified", [])    # list of {feature_id, fields:[...]}
    to_remove = data.get("removed", [])     # list of feature_ids

    try:
        fetched = fetch_roadmap_features()
        fetched_map = {f["feature_id"]: f for f in fetched}
        applied = 0

        for fid in to_add:
            f_data = fetched_map.get(fid)
            if not f_data:
                continue
            existing = Feature.query.filter_by(feature_id=fid).first()
            if existing:
                existing.is_deleted = False
                _apply_data(existing, f_data)
            else:
                new_feat = Feature()
                _apply_data(new_feat, f_data)
                db.session.add(new_feat)
            _log(fid, f_data.get("name", ""), "added")
            applied += 1

        for mod in to_modify:
            fid = mod["feature_id"]
            fields = mod.get("fields", [])
            existing = Feature.query.filter_by(feature_id=fid, is_deleted=False).first()
            f_data = fetched_map.get(fid)
            if not (existing and f_data):
                continue
            for field in fields:
                old_val = getattr(existing, field, None)
                new_val = f_data.get(field)
                setattr(existing, field, new_val)
                _log(fid, existing.name, "modified", field, old_val, new_val)
            existing.last_roadmap_update = f_data.get("last_roadmap_update") or datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            applied += 1

        for fid in to_remove:
            existing = Feature.query.filter_by(feature_id=fid, is_deleted=False).first()
            if existing:
                existing.is_deleted = True
                existing.updated_at = datetime.utcnow()
                _log(fid, existing.name, "removed")
                applied += 1

        db.session.commit()

        if sync_log_id:
            sl = SyncLog.query.get(sync_log_id)
            if sl:
                sl.status = "success"
                sl.completed_at = datetime.utcnow()
                db.session.commit()

        return jsonify({"status": "success", "applied": applied})

    except Exception as exc:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(exc)}), 500


def _apply_data(feature, data):
    fields = [
        "feature_id", "name", "workload", "description", "release_status",
        "release_phase", "ga_estimate", "confidence_level", "business_readiness",
        "platforms", "roadmap_link", "published_date", "last_roadmap_update",
        "source", "is_custom",
    ]
    for field in fields:
        if field in data:
            setattr(feature, field, data[field])


def _log(feature_id, feature_name, change_type, field_name=None, old_val=None, new_val=None):
    entry = ChangeLog(
        feature_id=feature_id,
        feature_name=feature_name,
        field_name=field_name or change_type,
        old_value=str(old_val) if old_val is not None else None,
        new_value=str(new_val) if new_val is not None else None,
        change_type=change_type,
        detected_at=datetime.utcnow(),
        applied=True,
        applied_at=datetime.utcnow(),
    )
    db.session.add(entry)

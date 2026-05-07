import json
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from app import db
from app.models import CustomColumn, CustomColumnValue, Feature, FeatureNote

features_bp = Blueprint("features", __name__)


@features_bp.route("/")
def index():
    features = (
        Feature.query.filter_by(is_deleted=False)
        .order_by(Feature.workload, Feature.name)
        .all()
    )
    custom_columns = CustomColumn.query.order_by(CustomColumn.display_order).all()
    custom_columns_data = [c.to_dict() for c in custom_columns]
    filter_options = {
        "workloads": sorted({f.workload for f in features if f.workload}),
        "statuses": ["GA", "Rolling Out", "In Development"],
        "phases": ["General Availability", "Targeted Release", "Preview", "Frontier"],
        "ga_estimates": sorted({f.ga_estimate for f in features if f.ga_estimate}),
        "readiness": ["Safe to Promote", "Pilot Only", "Do Not Commit"],
    }
    return render_template(
        "features.html",
        features=features,
        custom_columns=custom_columns,
        custom_columns_data=custom_columns_data,
        filter_options=filter_options,
    )


@features_bp.route("/api/list")
def api_list():
    features = Feature.query.filter_by(is_deleted=False).order_by(Feature.workload, Feature.name).all()
    custom_columns = CustomColumn.query.order_by(CustomColumn.display_order).all()
    return jsonify({
        "features": [f.to_dict() for f in features],
        "custom_columns": [c.to_dict() for c in custom_columns],
    })


@features_bp.route("/api/update/<int:feature_id>", methods=["POST"])
def update_feature(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    data = request.get_json()
    editable = [
        "name", "workload", "release_status", "release_phase", "ga_estimate",
        "confidence_level", "business_readiness", "visible_in_tenant", "license_required",
        "description",
    ]
    for field in editable:
        if field in data:
            setattr(feature, field, data[field])
    feature.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})


@features_bp.route("/api/add", methods=["POST"])
def add_feature():
    data = request.get_json()
    feature = Feature(
        feature_id=f"custom-{int(datetime.utcnow().timestamp() * 1000)}",
        name=data.get("name", "New Feature"),
        workload=data.get("workload", ""),
        release_status=data.get("release_status", "In Development"),
        release_phase=data.get("release_phase", "Preview"),
        ga_estimate=data.get("ga_estimate", ""),
        confidence_level=data.get("confidence_level", "Low"),
        business_readiness=data.get("business_readiness", "Pilot Only"),
        visible_in_tenant=data.get("visible_in_tenant", ""),
        license_required=data.get("license_required", ""),
        description=data.get("description", ""),
        source="custom",
        is_custom=True,
    )
    db.session.add(feature)
    db.session.commit()
    return jsonify({"success": True, "id": feature.id, "feature": feature.to_dict()})


@features_bp.route("/api/delete/<int:feature_id>", methods=["DELETE"])
def delete_feature(feature_id):
    feature = Feature.query.get_or_404(feature_id)
    feature.is_deleted = True
    feature.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})


# ── Notes ──────────────────────────────────────────────────────────────────────

@features_bp.route("/api/<int:feature_id>/notes", methods=["GET"])
def get_notes(feature_id):
    notes = FeatureNote.query.filter_by(feature_id=feature_id).order_by(FeatureNote.created_at).all()
    return jsonify([{"id": n.id, "note": n.note, "updated_at": n.updated_at.isoformat()} for n in notes])


@features_bp.route("/api/<int:feature_id>/notes", methods=["POST"])
def add_note(feature_id):
    Feature.query.get_or_404(feature_id)
    data = request.get_json()
    note = FeatureNote(feature_id=feature_id, note=data["note"])
    db.session.add(note)
    db.session.commit()
    return jsonify({"success": True, "id": note.id})


@features_bp.route("/api/notes/<int:note_id>", methods=["PUT"])
def update_note(note_id):
    note = FeatureNote.query.get_or_404(note_id)
    note.note = request.get_json()["note"]
    note.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"success": True})


@features_bp.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    note = FeatureNote.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"success": True})


# ── Custom Columns ─────────────────────────────────────────────────────────────

@features_bp.route("/api/columns", methods=["GET"])
def get_columns():
    cols = CustomColumn.query.order_by(CustomColumn.display_order).all()
    return jsonify([c.to_dict() for c in cols])


@features_bp.route("/api/columns", methods=["POST"])
def add_column():
    data = request.get_json()
    max_order = db.session.query(db.func.max(CustomColumn.display_order)).scalar() or 0
    col = CustomColumn(
        name=data["name"],
        column_type=data.get("type", "text"),
        options=json.dumps(data.get("options", [])),
        display_order=max_order + 1,
    )
    db.session.add(col)
    db.session.commit()
    return jsonify({"success": True, "column": col.to_dict()})


@features_bp.route("/api/columns/<int:col_id>", methods=["DELETE"])
def delete_column(col_id):
    col = CustomColumn.query.get_or_404(col_id)
    db.session.delete(col)
    db.session.commit()
    return jsonify({"success": True})


@features_bp.route("/api/custom-value", methods=["POST"])
def set_custom_value():
    data = request.get_json()
    val = CustomColumnValue.query.filter_by(
        feature_id=data["feature_id"], column_id=data["column_id"]
    ).first()
    if val:
        val.value = data["value"]
        val.updated_at = datetime.utcnow()
    else:
        val = CustomColumnValue(
            feature_id=data["feature_id"],
            column_id=data["column_id"],
            value=data["value"],
        )
        db.session.add(val)
    db.session.commit()
    return jsonify({"success": True})

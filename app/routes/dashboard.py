from flask import Blueprint, jsonify, render_template

from app import db
from app.models import Feature, SyncLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    features = Feature.query.filter_by(is_deleted=False).order_by(Feature.workload, Feature.name).all()
    last_sync = SyncLog.query.filter_by(status="success").order_by(SyncLog.completed_at.desc()).first()

    total = len(features)
    stats = {
        "total": total,
        "ga": sum(1 for f in features if f.release_status == "GA"),
        "rolling_out": sum(1 for f in features if f.release_status == "Rolling Out"),
        "in_dev": sum(1 for f in features if f.release_status == "In Development"),
        "frontier": sum(1 for f in features if f.release_phase == "Frontier"),
        "safe": sum(1 for f in features if f.business_readiness == "Safe to Promote"),
        "pilot": sum(1 for f in features if f.business_readiness == "Pilot Only"),
        "do_not": sum(1 for f in features if f.business_readiness == "Do Not Commit"),
        "high_conf": sum(1 for f in features if f.confidence_level == "High"),
        "medium_conf": sum(1 for f in features if f.confidence_level == "Medium"),
        "low_conf": sum(1 for f in features if f.confidence_level == "Low"),
        "custom": sum(1 for f in features if f.is_custom),
    }

    workload_counts: dict[str, int] = {}
    ga_timeline: dict[str, int] = {}
    for f in features:
        wl = f.workload or "Other"
        workload_counts[wl] = workload_counts.get(wl, 0) + 1
        if f.ga_estimate and f.release_status != "GA":
            ga_timeline[f.ga_estimate] = ga_timeline.get(f.ga_estimate, 0) + 1

    filter_options = {
        "workloads": sorted({f.workload for f in features if f.workload}),
        "statuses": ["GA", "Rolling Out", "In Development"],
        "phases": ["General Availability", "Targeted Release", "Preview", "Frontier"],
        "ga_estimates": sorted({f.ga_estimate for f in features if f.ga_estimate}),
        "readiness": ["Safe to Promote", "Pilot Only", "Do Not Commit"],
    }

    return render_template(
        "dashboard.html",
        features=features,
        stats=stats,
        workload_counts=workload_counts,
        ga_timeline=ga_timeline,
        last_sync=last_sync,
        filter_options=filter_options,
    )


@dashboard_bp.route("/api/chart-data")
def chart_data():
    features = Feature.query.filter_by(is_deleted=False).all()

    status_data: dict[str, int] = {}
    phase_data: dict[str, int] = {}
    readiness_data: dict[str, int] = {}
    confidence_data: dict[str, int] = {}
    workload_data: dict[str, int] = {}
    ga_timeline: dict[str, int] = {}

    for f in features:
        status_data[f.release_status or "Unknown"] = status_data.get(f.release_status or "Unknown", 0) + 1
        phase_data[f.release_phase or "Unknown"] = phase_data.get(f.release_phase or "Unknown", 0) + 1
        readiness_data[f.business_readiness or "Unknown"] = readiness_data.get(f.business_readiness or "Unknown", 0) + 1
        confidence_data[f.confidence_level or "Unknown"] = confidence_data.get(f.confidence_level or "Unknown", 0) + 1
        wl = f.workload or "Other"
        workload_data[wl] = workload_data.get(wl, 0) + 1
        if f.ga_estimate and f.release_status != "GA":
            ga_timeline[f.ga_estimate] = ga_timeline.get(f.ga_estimate, 0) + 1

    return jsonify({
        "status": status_data,
        "phase": phase_data,
        "readiness": readiness_data,
        "confidence": confidence_data,
        "workload": workload_data,
        "ga_timeline": ga_timeline,
    })

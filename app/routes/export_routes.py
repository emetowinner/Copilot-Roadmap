from datetime import datetime

from flask import Blueprint, request, send_file

from app.models import CustomColumn, CustomColumnValue, Feature
from app.services.excel_exporter import export_features_to_excel

export_bp = Blueprint("export", __name__)


@export_bp.route("/excel")
def export_excel():
    query = Feature.query.filter_by(is_deleted=False)

    workloads   = request.args.getlist("workload")
    statuses    = request.args.getlist("status")
    phases      = request.args.getlist("phase")
    ga_estimates = request.args.getlist("ga")
    readiness   = request.args.getlist("readiness")

    if workloads:
        query = query.filter(Feature.workload.in_(workloads))
    if statuses:
        query = query.filter(Feature.release_status.in_(statuses))
    if phases:
        query = query.filter(Feature.release_phase.in_(phases))
    if ga_estimates:
        query = query.filter(Feature.ga_estimate.in_(ga_estimates))
    if readiness:
        query = query.filter(Feature.business_readiness.in_(readiness))

    features = query.order_by(Feature.workload, Feature.name).all()

    custom_columns = CustomColumn.query.order_by(CustomColumn.display_order).all()
    feature_ids = [f.id for f in features]
    all_values = CustomColumnValue.query.filter(
        CustomColumnValue.feature_id.in_(feature_ids)
    ).all() if feature_ids else []
    custom_values_map = {(v.feature_id, v.column_id): v.value for v in all_values}

    output = export_features_to_excel(features, custom_columns, custom_values_map)

    active = sum([bool(workloads), bool(statuses), bool(phases), bool(ga_estimates), bool(readiness)])
    suffix = f"_filtered" if active else ""
    filename = f"Copilot_Feature_Matrix{suffix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )

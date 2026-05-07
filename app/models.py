from datetime import datetime
from app import db


class Feature(db.Model):
    __tablename__ = "features"

    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(512), nullable=False)
    workload = db.Column(db.String(128))
    description = db.Column(db.Text)
    release_status = db.Column(db.String(64))   # GA, Rolling Out, In Development
    release_phase = db.Column(db.String(64))    # General Availability, Targeted Release, Preview, Frontier
    ga_estimate = db.Column(db.String(64))
    confidence_level = db.Column(db.String(32)) # High, Medium, Low
    business_readiness = db.Column(db.String(64))  # Safe to Promote, Pilot Only, Do Not Commit
    visible_in_tenant = db.Column(db.String(64))
    license_required = db.Column(db.String(256))
    platforms = db.Column(db.String(256))
    roadmap_link = db.Column(db.String(512))
    source = db.Column(db.String(32), default="roadmap")  # roadmap, custom
    is_custom = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    published_date = db.Column(db.DateTime)
    last_roadmap_update = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    notes = db.relationship("FeatureNote", backref="feature", lazy=True, cascade="all, delete-orphan")
    custom_values = db.relationship("CustomColumnValue", backref="feature", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "feature_id": self.feature_id,
            "name": self.name,
            "workload": self.workload or "",
            "description": self.description or "",
            "release_status": self.release_status or "",
            "release_phase": self.release_phase or "",
            "ga_estimate": self.ga_estimate or "",
            "confidence_level": self.confidence_level or "",
            "business_readiness": self.business_readiness or "",
            "visible_in_tenant": self.visible_in_tenant or "",
            "license_required": self.license_required or "",
            "platforms": self.platforms or "",
            "roadmap_link": self.roadmap_link or "",
            "source": self.source or "roadmap",
            "is_custom": self.is_custom,
            "notes": [{"id": n.id, "note": n.note} for n in self.notes],
            "custom_values": {str(v.column_id): v.value for v in self.custom_values},
            "last_roadmap_update": self.last_roadmap_update.strftime("%Y-%m-%d") if self.last_roadmap_update else "",
        }


class FeatureNote(db.Model):
    __tablename__ = "feature_notes"

    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.Integer, db.ForeignKey("features.id"), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomColumn(db.Model):
    __tablename__ = "custom_columns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    column_type = db.Column(db.String(32), default="text")  # text, date, dropdown, checkbox
    options = db.Column(db.Text, default="[]")  # JSON array for dropdown options
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    values = db.relationship("CustomColumnValue", backref="column", lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "name": self.name,
            "type": self.column_type,
            "options": json.loads(self.options or "[]"),
            "display_order": self.display_order,
        }


class CustomColumnValue(db.Model):
    __tablename__ = "custom_column_values"

    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.Integer, db.ForeignKey("features.id"), nullable=False)
    column_id = db.Column(db.Integer, db.ForeignKey("custom_columns.id"), nullable=False)
    value = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("feature_id", "column_id"),)


class ChangeLog(db.Model):
    __tablename__ = "change_log"

    id = db.Column(db.Integer, primary_key=True)
    feature_id = db.Column(db.String(128))
    feature_name = db.Column(db.String(512))
    field_name = db.Column(db.String(128))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    change_type = db.Column(db.String(32))  # added, modified, removed
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    applied = db.Column(db.Boolean, default=False)
    applied_at = db.Column(db.DateTime)


class SyncLog(db.Model):
    __tablename__ = "sync_log"

    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(32), default="refresh")
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    items_fetched = db.Column(db.Integer, default=0)
    items_added = db.Column(db.Integer, default=0)
    items_modified = db.Column(db.Integer, default=0)
    items_removed = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="running")  # running, success, failed
    error_message = db.Column(db.Text)

from services.db import db
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(50), default='analyst')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f'<User {self.email}>'
    
    # -----------------
    # Password helpers
    # -----------------
    def set_password(self, password: str):
        """Hashes the password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Checks a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

class File(db.Model):
    __tablename__ = 'files'

    file_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'))
    filename = db.Column(db.String(255))
    file_hash = db.Column(db.String(64), nullable=False)
    file_data = db.Column(db.LargeBinary)
    upload_date = db.Column(db.DateTime(timezone=True), server_default=func.now())
    status = db.Column(db.Integer, default=0)  # 0: uploaded, 1: processed, 2: failed
    __table_args__ = (db.UniqueConstraint('user_id', 'project_id', 'file_hash', name='unique_user_project_file_hash'),)

    def __repr__(self):
        return f'<File {self.filename}>'
    
class BpmnFile(db.Model):
    __tablename__ = "bpmn_files"

    bpmnfile_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.project_id"), nullable=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, server_default="")
    file_hash = db.Column(db.String(64), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)  # BYTEA → LargeBinary
    upload_date = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_modified = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    status = db.Column(db.Integer, default=0, nullable=False)  #  0: uploaded, 1: processed, 2: failed
    version = db.Column(db.Float, default=1, nullable=False)

    project = relationship('Project', back_populates='bpmn_files')
    audits = relationship("BpmnFileAudit", backref="bpmn_file", cascade="all, delete-orphan")
    approvals = relationship("BpmnApproval", back_populates="bpmn_file", cascade="all, delete-orphan")

    __table_args__ = (
    db.UniqueConstraint("user_id", "file_hash", "version", name="unique_user_file_hash_version_bpmn_files"),
    )

    def __repr__(self):
        return f"<BPMNFile {self.filename} (User {self.user_id})>"
    
class BpmnFileAudit(db.Model):
    __tablename__ = "bpmn_files_audit"

    audit_id = db.Column(db.Integer, primary_key=True)
    bpmnfile_id = db.Column(db.Integer, db.ForeignKey("bpmn_files.bpmnfile_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=False)
    save_date = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    approval_status = db.Column(db.Boolean, nullable=True)
    version = db.Column(db.Float, nullable=False)

    __table_args__ = (
    db.UniqueConstraint("user_id", "file_hash", "version", name="unique_user_file_hash_version_bpmn_files_audit"),
    )

    def __repr__(self):
        return f"<BPMNFile {self.filename} (User {self.user_id})>"
    
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)  # NULL => global
    type = db.Column(db.String(64), nullable=False)          # "Login Events" | "Recommendations" | "Validations"
    message = db.Column(db.Text, nullable=False)
    target_url = db.Column(db.String(255), nullable=False)
    read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), index=True)

class Project(db.Model):
    __tablename__ = 'projects'
    project_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    project_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=db.func.now())
    assigned_bpo_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    creator = relationship('User', foreign_keys=[user_id])
    assigned_bpo = relationship('User', foreign_keys=[assigned_bpo_id])

    files = relationship('File', backref='project', lazy=True, cascade="all, delete-orphan")
    bpmn_files = relationship('BpmnFile', back_populates='project', lazy=True, cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint('user_id', 'project_name'),)

    def __repr__(self):
        return f'<Project {self.project_name}>'
    
class EventLog(db.Model):
    __tablename__ = 'event_log'

    event_id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(
        db.Integer,
        db.ForeignKey('projects.project_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    file_id = db.Column(
        db.Integer,
        db.ForeignKey('files.file_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    case_id = db.Column(db.String(255), nullable=True)

    activity = db.Column(db.String(255), nullable=False)

    canonical_activity = db.Column(db.String(255), nullable=True)

    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    file = relationship('File', backref=db.backref('event_logs', cascade='all, delete-orphan'))
    project = relationship('Project', backref=db.backref('event_logs', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<EventLog event_id={self.event_id}>'


class MergeRun(db.Model):
    __tablename__ = "merge_runs"

    merge_run_id = db.Column(db.Integer, primary_key=True)
    project_id   = db.Column(db.Integer, db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    created_at   = db.Column(db.DateTime(timezone=True), server_default=db.func.now(), nullable=False)
    status       = db.Column(db.String(32), nullable=False, default="completed")
    event_count  = db.Column(db.Integer, nullable=False, default=0)
    source_fingerprints = db.Column(db.Text)  # optional

    project = relationship('Project', backref=db.backref('merge_runs', cascade='all, delete-orphan'))

class ConsolidatedEvent(db.Model):
    __tablename__ = "consolidated_event_log"

    id           = db.Column(db.BigInteger, primary_key=True)
    merge_run_id = db.Column(db.Integer, db.ForeignKey('merge_runs.merge_run_id', ondelete='CASCADE'), nullable=False, index=True)
    project_id   = db.Column(db.Integer, db.ForeignKey('projects.project_id', ondelete='CASCADE'), nullable=False, index=True)

    case_id            = db.Column(db.String(255))
    activity           = db.Column(db.String(255), nullable=False)
    canonical_activity = db.Column(db.String(255))
    timestamp          = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    source             = db.Column(db.String(255))

    run = relationship('MergeRun', backref=db.backref('events', cascade='all, delete-orphan'))

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    recommendation_id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    bottleneck_activity = db.Column(db.String(255), nullable=False)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=False)
    
    user = db.relationship('User', backref=db.backref('recommendations', lazy='dynamic'))
    project = db.relationship(
            'Project', 
            backref=db.backref('recommendations', lazy='dynamic', cascade="all, delete-orphan")
        )

    def __repr__(self):
        return f'<Recommendation id={self.recommendation_id} project_id={self.project_id}>'
    
class BottleneckMetric(db.Model):
    __tablename__ = "bottleneck_metrics"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.project_id"), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False)  # "activity" | "transition"
    # For activities
    activity = db.Column(db.String(255))
    # For transitions
    source_activity = db.Column(db.String(255))
    target_activity = db.Column(db.String(255))

    count = db.Column(db.Integer, default=0)
    avg_seconds = db.Column(db.Float)
    median_seconds = db.Column(db.Float)
    p90_seconds = db.Column(db.Float)
    is_bottleneck = db.Column(db.Boolean, default=False)

    # optional: BPMN node or edge id (if you later map canonical labels to BPMN IDs)
    bpmn_element_id = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    project = db.relationship(
            "Project", 
            backref=db.backref("bottleneck_metrics", lazy="dynamic", cascade="all, delete-orphan")
        )

class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False, index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.project_id'), nullable=True, index=True) # Optional link to project
    action = db.Column(db.String(255), nullable=False) # e.g., "Process Created", "File Uploaded"
    details = db.Column(db.Text, nullable=True) # More specific info
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship('User', backref='audit_logs')
    project = db.relationship(
            'Project', 
            backref=db.backref('audit_logs', lazy='dynamic', cascade="all, delete-orphan")
        )
    def __repr__(self):
        return f'<AuditLog {self.log_id} - User {self.user_id} - Action {self.action}>'
    
class BpmnApproval(db.Model):
    __tablename__ = "approvals"

    approval_id = db.Column(db.Integer, primary_key=True)
    bpmnfile_id = db.Column(db.Integer, db.ForeignKey("bpmn_files.bpmnfile_id"), nullable=False)
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=False)
    reviewed_by = db.Column(db.Integer, db.ForeignKey("users.user_id"), nullable=True)
    from_state = db.Column(db.String(20), nullable=False)
    to_state = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Pending", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = db.Column(db.DateTime(timezone=True), onupdate=func.now(), nullable=True)
    comment = db.Column(db.String(255), nullable=False)
    version = db.Column(db.Float, default=1, nullable=False)

    bpmn_file = relationship("BpmnFile", back_populates="approvals")
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<Approval {self.approval_id} for BPMN {self.bpmnfile_id} ({self.status})>"
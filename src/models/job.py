"""
Job model for the scheduler microservice
"""
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Index
import uuid
import json
from enum import Enum

from src.common.extensions import db

class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

class JobType(Enum):
    """Job type enumeration"""
    EMAIL_NOTIFICATION = "email_notification"
    DATA_PROCESSING = "data_processing"
    REPORT_GENERATION = "report_generation"
    CLEANUP_TASK = "cleanup_task"
    BACKUP_TASK = "backup_task"
    CUSTOM = "custom"

class Job(db.Model):
    """Job model with comprehensive scheduling information"""
    __tablename__ = 'jobs'
    
    # Primary key
    id = db.Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    # Basic job information
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text)
    job_type = db.Column(db.Enum(JobType), nullable=False, default=JobType.CUSTOM)
    
    # Scheduling information
    cron_expression = db.Column(db.String(100))  # e.g., "0 9 * * 1" for every Monday at 9 AM
    interval_seconds = db.Column(db.Integer)  # For interval-based jobs
    next_run_time = db.Column(db.DateTime(timezone=True), index=True)
    last_run_time = db.Column(db.DateTime(timezone=True))
    
    # Job configuration and parameters
    job_data = db.Column(JSONB)
    max_retries = db.Column(db.Integer, default=3)
    retry_count = db.Column(db.Integer, default=0)
    timeout_seconds = db.Column(db.Integer, default=3600)  # 1 hour default
    
    # Status and tracking
    status = db.Column(db.Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    is_active = db.Column(db.Boolean, default=True, index=True)
    priority = db.Column(db.Integer, default=5, index=True)  # 1-10, higher = more priority
    
    # Execution tracking
    total_runs = db.Column(db.Integer, default=0)
    successful_runs = db.Column(db.Integer, default=0)
    failed_runs = db.Column(db.Integer, default=0)
    average_runtime = db.Column(db.Float, default=0.0)  # in seconds
    
    # Metadata
    created_by = db.Column(db.String(255), index=True)  # User ID or service name
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True), 
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc)
    )
    
    # Relationships
    executions = db.relationship('JobExecution', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_job_next_run_active', 'next_run_time', 'is_active'),
        Index('idx_job_status_type', 'status', 'job_type'),
        Index('idx_job_created_by_status', 'created_by', 'status'),
        Index('idx_job_priority_next_run', 'priority', 'next_run_time'),
    )
    
    def __repr__(self):
        return f'<Job {self.name} ({self.id})>'
    
    def to_dict(self, include_sensitive=False):
        """Convert job to dictionary representation"""
        data = {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'job_type': self.job_type.value if self.job_type else None,
            'status': self.status.value if self.status else None,
            'is_active': self.is_active,
            'priority': self.priority,
            'cron_expression': self.cron_expression,
            'interval_seconds': self.interval_seconds,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'average_runtime': self.average_runtime,
            'max_retries': self.max_retries,
            'retry_count': self.retry_count,
            'timeout_seconds': self.timeout_seconds,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            # Parse job_data JSON if it's stored as string
            try:
                data['job_data'] = json.loads(self.job_data) if isinstance(self.job_data, str) else self.job_data
            except (json.JSONDecodeError, TypeError):
                data['job_data'] = self.job_data
        
        return data
    
    @classmethod
    def get_active_jobs(cls):
        """Get all active jobs"""
        return cls.query.filter_by(is_active=True).all()
    
    @classmethod
    def get_pending_jobs(cls):
        """Get all pending jobs"""
        return cls.query.filter_by(status=JobStatus.PENDING, is_active=True).all()
    
    @classmethod
    def get_jobs_by_user(cls, user_id, page=1, per_page=20):
        """Get paginated jobs for a specific user"""
        return cls.query.filter_by(created_by=user_id).paginate(
            page=page, per_page=per_page, error_out=False
        )


class JobExecution(db.Model):
    """Job execution history model"""
    __tablename__ = 'job_executions'
    
    id = db.Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    job_id = db.Column(UUID(as_uuid=True), db.ForeignKey('jobs.id'), nullable=False, index=True)
    
    # Execution details
    started_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime(timezone=True))
    duration = db.Column(db.Float)  # in seconds
    status = db.Column(db.Enum(JobStatus), nullable=False)
    
    # Results and errors
    result = db.Column(db.Text)
    error_message = db.Column(db.Text)
    stack_trace = db.Column(db.Text)
    
    # Execution context
    worker_node = db.Column(db.String(255))  # Which server/container executed the job
    execution_context = db.Column(JSONB)
    
    def __repr__(self):
        return f'<JobExecution {self.id} for Job {self.job_id}>'
    
    def to_dict(self):
        """Convert execution to dictionary"""
        return {
            'id': str(self.id),
            'job_id': str(self.job_id),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'duration': self.duration,
            'status': self.status.value if self.status else None,
            'result': self.result,
            'error_message': self.error_message,
            'worker_node': self.worker_node,
        }
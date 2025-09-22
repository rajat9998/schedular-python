"""
Job service layer - Business logic for job management
Implements SOLID principles with proper separation of concerns
"""
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from croniter import croniter

from src.models.job import Job, JobExecution, JobStatus, JobType
from src.common.exceptions import JobNotFoundError, InvalidJobConfigurationError
from src.common.extensions import db
from src.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)

class JobService:
    """
    Job service implementing business logic for job management
    Following Single Responsibility Principle
    """
    
    def __init__(self, scheduler_service: SchedulerService = None):
        self.scheduler_service = scheduler_service or SchedulerService()
    
    def create_job(self, job_data: Dict[str, Any]) -> Job:
        """
        Create a new job with validation
        
        Args:
            job_data: Dictionary containing job configuration
            
        Returns:
            Job: Created job instance
            
        Raises:
            InvalidJobConfigurationError: If job configuration is invalid
        """
        try:
            # Validate job data
            self._validate_job_data(job_data)
            
            # Create job instance
            job = Job(
                name=job_data['name'],
                description=job_data.get('description', ''),
                job_type=JobType(job_data.get('job_type', 'custom')),
                cron_expression=job_data.get('cron_expression'),
                interval_seconds=job_data.get('interval_seconds'),
                job_data=json.dumps(job_data.get('job_data', {})),
                max_retries=job_data.get('max_retries', 3),
                timeout_seconds=job_data.get('timeout_seconds', 3600),
                priority=job_data.get('priority', 5),
                created_by=job_data.get('created_by', 'system')
            )
            
            # Calculate next run time
            job.next_run_time = self._calculate_next_run_time(
                job.cron_expression, 
                job.interval_seconds
            )
            
            # Save to database
            db.session.add(job)
            db.session.commit()
            
            # Schedule job in APScheduler
            if job.is_active and job.next_run_time:
                self.scheduler_service.schedule_job(job)
            
            logger.info(f"Created job: {job.name} (ID: {job.id})")
            return job
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating job: {str(e)}")
            raise InvalidJobConfigurationError(f"Failed to create job: {str(e)}")
    
    def get_job_by_id(self, job_id: str) -> Job:
        """
        Retrieve job by ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job: Job instance
            
        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = Job.query.get(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID {job_id} not found")
        return job
    
    def get_all_jobs(self, 
                    page: int = 1, 
                    per_page: int = 20,
                    filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get paginated list of jobs with optional filtering
        
        Args:
            page: Page number
            per_page: Items per page
            filters: Optional filters (status, job_type, created_by)
            
        Returns:
            Dict containing jobs and pagination info
        """
        query = Job.query
        
        # Apply filters
        if filters:
            if 'status' in filters:
                query = query.filter(Job.status == JobStatus(filters['status']))
            if 'job_type' in filters:
                query = query.filter(Job.job_type == JobType(filters['job_type']))
            if 'created_by' in filters:
                query = query.filter(Job.created_by == filters['created_by'])
            if 'is_active' in filters:
                query = query.filter(Job.is_active == filters['is_active'])
        
        # Order by priority (desc) and created_at (desc)
        query = query.order_by(Job.priority.desc(), Job.created_at.desc())
        
        # Paginate
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return {
            'jobs': [job.to_dict() for job in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> Job:
        """
        Update job configuration
        
        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update
            
        Returns:
            Job: Updated job instance
        """
        job = self.get_job_by_id(job_id)
        
        try:
            # Update allowed fields
            allowed_fields = [
                'name', 'description', 'cron_expression', 'interval_seconds',
                'job_data', 'max_retries', 'timeout_seconds', 'priority', 'is_active'
            ]
            
            for field, value in updates.items():
                if field in allowed_fields:
                    if field == 'job_data' and isinstance(value, dict):
                        setattr(job, field, json.dumps(value))
                    else:
                        setattr(job, field, value)
            
            # Recalculate next run time if scheduling changed
            if any(field in updates for field in ['cron_expression', 'interval_seconds']):
                job.next_run_time = self._calculate_next_run_time(
                    job.cron_expression, 
                    job.interval_seconds
                )
                # Reschedule in APScheduler
                self.scheduler_service.reschedule_job(job)
            
            job.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            logger.info(f"Updated job: {job.name} (ID: {job.id})")
            return job
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating job {job_id}: {str(e)}")
            raise InvalidJobConfigurationError(f"Failed to update job: {str(e)}")
    
    def delete_job(self, job_id: str) -> None:
        """
        Delete job and remove from scheduler
        
        Args:
            job_id: Job identifier
        """
        job = self.get_job_by_id(job_id)
        
        try:
            # Remove from scheduler
            self.scheduler_service.remove_job(str(job.id))
            
            # Delete from database (cascades to executions)
            db.session.delete(job)
            db.session.commit()
            
            logger.info(f"Deleted job: {job.name} (ID: {job.id})")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            raise
    
    def pause_job(self, job_id: str) -> Job:
        """Pause job execution"""
        job = self.get_job_by_id(job_id)
        job.is_active = False
        job.status = JobStatus.PAUSED
        db.session.commit()
        
        # Remove from scheduler
        self.scheduler_service.remove_job(str(job.id))
        
        logger.info(f"Paused job: {job.name} (ID: {job.id})")
        return job
    
    def resume_job(self, job_id: str) -> Job:
        """Resume job execution"""
        job = self.get_job_by_id(job_id)
        job.is_active = True
        job.status = JobStatus.PENDING
        job.next_run_time = self._calculate_next_run_time(
            job.cron_expression, 
            job.interval_seconds
        )
        db.session.commit()
        
        # Add back to scheduler
        self.scheduler_service.schedule_job(job)
        
        logger.info(f"Resumed job: {job.name} (ID: {job.id})")
        return job
    
    def get_job_executions(self, job_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get job execution history"""
        job = self.get_job_by_id(job_id)
        
        pagination = job.executions.order_by(
            JobExecution.started_at.desc()
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return {
            'executions': [execution.to_dict() for execution in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    
    def _validate_job_data(self, job_data: Dict[str, Any]) -> None:
        """
        Validate job configuration data
        
        Args:
            job_data: Job configuration dictionary
            
        Raises:
            InvalidJobConfigurationError: If validation fails
        """
        required_fields = ['name']
        for field in required_fields:
            if field not in job_data or not job_data[field]:
                raise InvalidJobConfigurationError(f"Missing required field: {field}")
        
        # Validate scheduling configuration
        if not job_data.get('cron_expression') and not job_data.get('interval_seconds'):
            raise InvalidJobConfigurationError(
                "Either cron_expression or interval_seconds must be provided"
            )
        
        # Validate cron expression
        if job_data.get('cron_expression'):
            try:
                croniter(job_data['cron_expression'])
            except Exception as e:
                raise InvalidJobConfigurationError(f"Invalid cron expression: {str(e)}")
        
        # Validate interval
        if job_data.get('interval_seconds'):
            interval = job_data['interval_seconds']
            if not isinstance(interval, int) or interval <= 0:
                raise InvalidJobConfigurationError("interval_seconds must be a positive integer")
        
        # Validate job type
        if job_data.get('job_type'):
            try:
                JobType(job_data['job_type'])
            except ValueError:
                valid_types = [jt.value for jt in JobType]
                raise InvalidJobConfigurationError(
                    f"Invalid job_type. Must be one of: {valid_types}"
                )
    
    def _calculate_next_run_time(self, 
                               cron_expression: Optional[str], 
                               interval_seconds: Optional[int]) -> Optional[datetime]:
        """
        Calculate next run time based on cron expression or interval
        
        Args:
            cron_expression: Cron expression string
            interval_seconds: Interval in seconds
            
        Returns:
            datetime: Next run time or None
        """
        now = datetime.now(timezone.utc)
        
        if cron_expression:
            try:
                cron = croniter(cron_expression, now)
                return cron.get_next(datetime)
            except Exception:
                logger.error(f"Error calculating next run time from cron: {cron_expression}")
                return None
        
        elif interval_seconds:
            from datetime import timedelta
            return now + timedelta(seconds=interval_seconds)
        
        return None
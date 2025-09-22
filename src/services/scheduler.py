"""
Scheduler service for managing APScheduler jobs
Handles the actual job scheduling and execution logic
"""

import logging
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.models.job import Job, JobExecution, JobStatus
from src.services.executor import JobExecutor
from src.common.extensions import db

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Service for managing job scheduling with APScheduler
    Implements Interface Segregation Principle
    """
    
    def __init__(self, scheduler: Optional[BackgroundScheduler] = None):
        self.scheduler = scheduler
        self.job_executor = JobExecutor()
    
    def set_scheduler(self, scheduler: BackgroundScheduler) -> None:
        """Set the scheduler instance (Dependency Injection)"""
        self.scheduler = scheduler
    
    def schedule_job(self, job: Job) -> None:
        """
        Schedule a job in APScheduler
        
        Args:
            job: Job instance to schedule
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return
        
        try:
            job_id = str(job.id)
            
            # Remove existing job if it exists
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Determine trigger type
            trigger = self._create_trigger(job)
            if not trigger:
                logger.error(f"Could not create trigger for job {job.name}")
                return
            
            # Schedule the job
            self.scheduler.add_job(
                func=self._execute_job,
                trigger=trigger,
                id=job_id,
                name=job.name,
                args=[job_id],
                max_instances=1,
                replace_existing=True,
                coalesce=True
            )
            
            logger.info(f"Scheduled job: {job.name} (ID: {job_id})")
            
        except Exception as e:
            logger.error(f"Error scheduling job {job.name}: {str(e)}")
            raise
    
    def reschedule_job(self, job: Job) -> None:
        """Reschedule an existing job with new configuration"""
        self.schedule_job(job)
    
    def remove_job(self, job_id: str) -> None:
        """
        Remove job from scheduler
        
        Args:
            job_id: Job identifier
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return
        
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed job from scheduler: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {str(e)}")
    
    def get_scheduled_jobs(self) -> list:
        """Get all scheduled jobs from APScheduler"""
        if not self.scheduler:
            return []
        return self.scheduler.get_jobs()
    
    def _create_trigger(self, job: Job):
        """
        Create appropriate trigger for job based on configuration
        
        Args:
            job: Job instance
            
        Returns:
            APScheduler trigger or None
        """
        if job.cron_expression:
            try:
                return CronTrigger.from_crontab(job.cron_expression, timezone='UTC')
            except Exception as e:
                logger.error(f"Invalid cron expression {job.cron_expression}: {str(e)}")
                return None
        
        elif job.interval_seconds:
            return IntervalTrigger(seconds=job.interval_seconds, timezone='UTC')
        
        return None
    
    def _execute_job(self, job_id: str) -> None:
        """
        Execute job by delegating to JobExecutor
        This method is called by APScheduler
        
        Args:
            job_id: Job identifier
        """
        try:
            # Get job from database
            job = Job.query.get(job_id)
            if not job or not job.is_active:
                logger.warning(f"Job {job_id} not found or inactive, skipping execution")
                return
            
            # Execute job
            self.job_executor.execute(job)
            
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {str(e)}")
            # Update job status in case of scheduler-level errors
            try:
                job = Job.query.get(job_id)
                if job:
                    job.status = JobStatus.FAILED
                    job.failed_runs += 1
                    db.session.commit()
            except Exception:
                pass  # Don't let database errors prevent error logging
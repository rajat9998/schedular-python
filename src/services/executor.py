"""
Job executor service - Handles the actual execution of jobs
Implements various job types with proper error handling and tracking
"""

import logging
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import socket
import threading

from src.models.job import Job, JobExecution, JobStatus, JobType
from src.common.extensions import db

logger = logging.getLogger(__name__)

class JobExecutor:
    """
    Job executor implementing the actual job execution logic
    Follows Single Responsibility and Open/Closed Principles
    """
    
    def __init__(self):
        self.worker_node = socket.gethostname()
        self.job_handlers = {
            JobType.EMAIL_NOTIFICATION: self._handle_email_notification,
            JobType.DATA_PROCESSING: self._handle_data_processing,
            JobType.REPORT_GENERATION: self._handle_report_generation,
            JobType.CLEANUP_TASK: self._handle_cleanup_task,
            JobType.BACKUP_TASK: self._handle_backup_task,
            JobType.CUSTOM: self._handle_custom_job
        }
    
    def execute(self, job: Job) -> JobExecution:
        """
        Execute a job and track its execution
        
        Args:
            job: Job instance to execute
            
        Returns:
            JobExecution: Execution record
        """
        # Create execution record
        execution = JobExecution(
            job_id=job.id,
            status=JobStatus.RUNNING,
            worker_node=self.worker_node,
            started_at=datetime.now(timezone.utc)
        )
        
        # Update job status
        job.status = JobStatus.RUNNING
        job.retry_count = getattr(job, 'current_retry', 0)
        
        try:
            db.session.add(execution)
            db.session.commit()
            
            logger.info(f"Starting execution of job: {job.name} (ID: {job.id})")
            
            # Execute the job with timeout
            start_time = time.time()
            result = self._execute_with_timeout(job, job.timeout_seconds)
            end_time = time.time()
            
            # Calculate duration
            duration = end_time - start_time
            
            # Update execution record
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration = duration
            execution.status = JobStatus.COMPLETED
            execution.result = str(result) if result else "Job completed successfully"
            
            # Update job statistics
            job.status = JobStatus.COMPLETED
            job.last_run_time = execution.started_at
            job.total_runs += 1
            job.successful_runs += 1
            job.retry_count = 0
            
            # Update average runtime
            job.average_runtime = (
                (job.average_runtime * (job.total_runs - 1) + duration) / job.total_runs
            )
            
            # Calculate next run time
            job.next_run_time = self._calculate_next_run_time(job)
            
            db.session.commit()
            logger.info(f"Job {job.name} completed successfully in {duration:.2f}s")
            
        except Exception as e:
            # Handle execution failure
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration = time.time() - start_time if 'start_time' in locals() else 0
            execution.status = JobStatus.FAILED
            execution.error_message = str(e)
            execution.stack_trace = traceback.format_exc()
            
            # Update job failure statistics
            job.status = JobStatus.FAILED
            job.total_runs += 1
            job.failed_runs += 1
            job.last_run_time = execution.started_at
            
            # Handle retries
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.PENDING
                job.next_run_time = self._calculate_retry_time(job)
                logger.warning(f"Job {job.name} failed, retry {job.retry_count}/{job.max_retries}")
            else:
                job.next_run_time = None
                logger.error(f"Job {job.name} failed permanently after {job.max_retries} retries")
            
            db.session.commit()
            logger.error(f"Job {job.name} failed: {str(e)}")
        
        return execution
    
    def _execute_with_timeout(self, job: Job, timeout_seconds: int) -> Any:
        """
        Execute job with timeout handling
        
        Args:
            job: Job to execute
            timeout_seconds: Maximum execution time
            
        Returns:
            Job execution result
        """
        result = None
        exception = None
        
        def target():
            nonlocal result, exception
            try:
                handler = self.job_handlers.get(job.job_type, self._handle_custom_job)
                result = handler(job)
            except Exception as e:
                exception = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout_seconds)
        
        if thread.is_alive():
            # Job timed out
            logger.error(f"Job {job.name} timed out after {timeout_seconds}s")
            raise TimeoutError(f"Job execution timed out after {timeout_seconds} seconds")
        
        if exception:
            raise exception
        
        return result
    
    def _handle_email_notification(self, job: Job) -> str:
        """
        Handle email notification job
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        # Extract email parameters
        recipient = job_data.get('recipient', 'user@example.com')
        subject = job_data.get('subject', 'Notification')
        body = job_data.get('body', 'This is a notification email.')
        
        # Simulate email sending
        logger.info(f"Sending email to {recipient}: {subject}")
        
        # In real implementation, integrate with email service (SendGrid, SES, etc.)
        # For demo, we'll simulate processing time
        time.sleep(1)
        
        return f"Email sent successfully to {recipient}"
    
    def _handle_data_processing(self, job: Job) -> str:
        """
        Handle data processing job
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        # Extract processing parameters
        dataset = job_data.get('dataset', 'default_dataset')
        operation = job_data.get('operation', 'analyze')
        parameters = job_data.get('parameters', {})
        
        logger.info(f"Processing dataset {dataset} with operation {operation}")
        
        # Simulate data processing
        records_processed = parameters.get('record_count', 1000)
        processing_time = records_processed / 1000  # 1 second per 1000 records
        time.sleep(min(processing_time, 10))  # Cap at 10 seconds for demo
        
        return f"Processed {records_processed} records from {dataset}"
    
    def _handle_report_generation(self, job: Job) -> str:
        """
        Handle report generation job
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        report_type = job_data.get('report_type', 'summary')
        date_range = job_data.get('date_range', 'last_week')
        format_type = job_data.get('format', 'pdf')
        
        logger.info(f"Generating {report_type} report for {date_range} in {format_type} format")
        
        # Simulate report generation
        time.sleep(2)
        
        report_path = f"/reports/{report_type}_{date_range}.{format_type}"
        return f"Report generated successfully: {report_path}"
    
    def _handle_cleanup_task(self, job: Job) -> str:
        """
        Handle cleanup task job
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        cleanup_type = job_data.get('cleanup_type', 'temp_files')
        retention_days = job_data.get('retention_days', 7)
        
        logger.info(f"Running cleanup task: {cleanup_type} (retention: {retention_days} days)")
        
        # Simulate cleanup operations
        time.sleep(1)
        
        files_cleaned = job_data.get('estimated_files', 100)
        space_freed = job_data.get('estimated_space_mb', 500)
        
        return f"Cleanup completed: {files_cleaned} files removed, {space_freed}MB freed"
    
    def _handle_backup_task(self, job: Job) -> str:
        """
        Handle backup task job
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        backup_type = job_data.get('backup_type', 'database')
        destination = job_data.get('destination', 's3://backups/')
        compression = job_data.get('compression', True)
        
        logger.info(f"Running backup: {backup_type} to {destination}")
        
        # Simulate backup process
        time.sleep(3)
        
        backup_size = job_data.get('estimated_size_gb', 2.5)
        backup_file = f"{backup_type}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return f"Backup completed: {backup_file} ({backup_size}GB) stored at {destination}"
    
    def _handle_custom_job(self, job: Job) -> str:
        """
        Handle custom job type
        
        Args:
            job: Job instance
            
        Returns:
            str: Execution result
        """
        job_data = self._parse_job_data(job.job_data)
        
        # Custom job logic based on job_data
        custom_operation = job_data.get('operation', 'default')
        parameters = job_data.get('parameters', {})
        
        logger.info(f"Executing custom job: {custom_operation}")
        
        # Simulate custom processing
        processing_time = parameters.get('duration', 1)
        time.sleep(min(processing_time, 30))  # Cap at 30 seconds
        
        return f"Custom job completed: {custom_operation}"
    
    def _parse_job_data(self, job_data: Any) -> Dict[str, Any]:
        """
        Parse job data from string or dict
        
        Args:
            job_data: Job data (string or dict)
            
        Returns:
            Dict: Parsed job data
        """
        if isinstance(job_data, str):
            try:
                return json.loads(job_data)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in job_data, using empty dict")
                return {}
        elif isinstance(job_data, dict):
            return job_data
        else:
            return {}
    
    def _calculate_next_run_time(self, job: Job) -> Optional[datetime]:
        """Calculate next run time for the job"""
        from croniter import croniter
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        
        if job.cron_expression:
            try:
                cron = croniter(job.cron_expression, now)
                return cron.get_next(datetime)
            except Exception:
                return None
        elif job.interval_seconds:
            return now + timedelta(seconds=job.interval_seconds)
        
        return None
    
    def _calculate_retry_time(self, job: Job) -> datetime:
        """Calculate next retry time with exponential backoff"""
        from datetime import timedelta
        
        # Exponential backoff: 2^retry_count minutes
        delay_minutes = 2 ** job.retry_count
        # Cap at 60 minutes
        delay_minutes = min(delay_minutes, 60)
        
        return datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
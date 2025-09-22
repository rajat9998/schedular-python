"""
Job management REST API endpoints
Implements clean API design with proper error handling and documentation
"""
import logging
from flask import request
from flask_restx import Namespace, Resource, fields, marshal_with

from src.services.jobs import JobService
from src.common.exceptions import JobNotFoundError, InvalidJobConfigurationError
from src.common.validators import validate_pagination

logger = logging.getLogger(__name__)

# Create namespace for jobs
jobs_ns = Namespace('jobs', description='Job management operations')

# Initialize job service
job_service = JobService()

# API Models for documentation and validation
job_data_model = jobs_ns.model('JobData', {
    'operation': fields.String(description='Operation to perform'),
    'parameters': fields.Raw(description='Operation parameters')
})

create_job_model = jobs_ns.model('CreateJob', {
    'name': fields.String(required=True, description='Job name', example='Weekly Report Generation'),
    'description': fields.String(description='Job description', example='Generate weekly sales report'),
    'job_type': fields.String(
        description='Job type', 
        example='report_generation',
        enum=['email_notification', 'data_processing', 'report_generation', 'cleanup_task', 'backup_task', 'custom']
    ),
    'cron_expression': fields.String(
        description='Cron expression for scheduling', 
        example='0 9 * * 1',
        help='Every Monday at 9 AM'
    ),
    'interval_seconds': fields.Integer(
        description='Interval in seconds (alternative to cron)', 
        example=3600,
        help='Run every hour'
    ),
    'job_data': fields.Nested(job_data_model, description='Job-specific configuration'),
    'max_retries': fields.Integer(description='Maximum retry attempts', default=3),
    'timeout_seconds': fields.Integer(description='Job timeout in seconds', default=3600),
    'priority': fields.Integer(description='Job priority (1-10, higher = more priority)', default=5),
    'created_by': fields.String(description='Job creator identifier', example='user123')
})

update_job_model = jobs_ns.model('UpdateJob', {
    'name': fields.String(description='Job name'),
    'description': fields.String(description='Job description'),
    'cron_expression': fields.String(description='Cron expression'),
    'interval_seconds': fields.Integer(description='Interval in seconds'),
    'job_data': fields.Nested(job_data_model, description='Job configuration'),
    'max_retries': fields.Integer(description='Maximum retries'),
    'timeout_seconds': fields.Integer(description='Timeout in seconds'),
    'priority': fields.Integer(description='Job priority'),
    'is_active': fields.Boolean(description='Job active status')
})

job_response_model = jobs_ns.model('JobResponse', {
    'id': fields.String(description='Job ID'),
    'name': fields.String(description='Job name'),
    'description': fields.String(description='Job description'),
    'job_type': fields.String(description='Job type'),
    'status': fields.String(description='Job status'),
    'is_active': fields.Boolean(description='Active status'),
    'priority': fields.Integer(description='Job priority'),
    'cron_expression': fields.String(description='Cron expression'),
    'interval_seconds': fields.Integer(description='Interval seconds'),
    'next_run_time': fields.String(description='Next execution time'),
    'last_run_time': fields.String(description='Last execution time'),
    'total_runs': fields.Integer(description='Total execution count'),
    'successful_runs': fields.Integer(description='Successful executions'),
    'failed_runs': fields.Integer(description='Failed executions'),
    'average_runtime': fields.Float(description='Average runtime in seconds'),
    'max_retries': fields.Integer(description='Maximum retries'),
    'retry_count': fields.Integer(description='Current retry count'),
    'timeout_seconds': fields.Integer(description='Timeout seconds'),
    'created_by': fields.String(description='Creator'),
    'created_at': fields.String(description='Creation timestamp'),
    'updated_at': fields.String(description='Last update timestamp')
})

jobs_list_response_model = jobs_ns.model('JobsListResponse', {
    'jobs': fields.List(fields.Nested(job_response_model), description='List of jobs'),
    'total': fields.Integer(description='Total number of jobs'),
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Items per page'),
    'pages': fields.Integer(description='Total pages'),
    'has_next': fields.Boolean(description='Has next page'),
    'has_prev': fields.Boolean(description='Has previous page')
})

execution_response_model = jobs_ns.model('ExecutionResponse', {
    'id': fields.String(description='Execution ID'),
    'job_id': fields.String(description='Job ID'),
    'started_at': fields.String(description='Start time'),
    'completed_at': fields.String(description='Completion time'),
    'duration': fields.Float(description='Duration in seconds'),
    'status': fields.String(description='Execution status'),
    'result': fields.String(description='Execution result'),
    'error_message': fields.String(description='Error message if failed'),
    'worker_node': fields.String(description='Worker node identifier')
})

executions_list_response_model = jobs_ns.model('ExecutionsListResponse', {
    'executions': fields.List(fields.Nested(execution_response_model), description='List of executions'),
    'total': fields.Integer(description='Total executions'),
    'page': fields.Integer(description='Current page'),
    'per_page': fields.Integer(description='Items per page'),
    'pages': fields.Integer(description='Total pages'),
    'has_next': fields.Boolean(description='Has next page'),
    'has_prev': fields.Boolean(description='Has previous page')
})

error_model = jobs_ns.model('Error', {
    'message': fields.String(description='Error message'),
    'code': fields.String(description='Error code'),
    'details': fields.Raw(description='Additional error details')
})

@jobs_ns.route('')
class JobListResource(Resource):
    """Job list resource"""
    
    @jobs_ns.doc('list_jobs')
    @jobs_ns.expect(jobs_ns.parser()
        .add_argument('page', type=int, default=1, help='Page number')
        .add_argument('per_page', type=int, default=20, help='Items per page')
        .add_argument('status', type=str, help='Filter by status')
        .add_argument('job_type', type=str, help='Filter by job type')
        .add_argument('created_by', type=str, help='Filter by creator')
        .add_argument('is_active', type=bool, help='Filter by active status')
    )
    @jobs_ns.marshal_with(jobs_list_response_model)
    @jobs_ns.response(200, 'Success')
    @jobs_ns.response(400, 'Bad Request', error_model)
    def get(self):
        """
        List all jobs with optional filtering and pagination
        
        Returns paginated list of jobs with filtering options
        """
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # Validate pagination
            page, per_page = validate_pagination(page, per_page)
            
            # Build filters
            filters = {}
            for param in ['status', 'job_type', 'created_by']:
                value = request.args.get(param)
                if value:
                    filters[param] = value
            
            # Handle boolean filter
            is_active = request.args.get('is_active')
            if is_active is not None:
                filters['is_active'] = is_active.lower() == 'true'
            
            # Get jobs
            result = job_service.get_all_jobs(
                page=page, 
                per_page=per_page, 
                filters=filters
            )
            
            return result, 200
            
        except Exception as e:
            logger.error(f"Error listing jobs: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")
    
    @jobs_ns.doc('create_job')
    @jobs_ns.expect(create_job_model, validate=True)
    @jobs_ns.marshal_with(job_response_model)
    @jobs_ns.response(201, 'Job created successfully')
    @jobs_ns.response(400, 'Invalid job configuration', error_model)
    @jobs_ns.response(422, 'Validation error', error_model)
    def post(self):
        """
        Create a new job
        
        Creates a new scheduled job with the provided configuration
        """
        try:
            job_data = request.get_json()
            
            # Create job
            job = job_service.create_job(job_data)
            
            logger.info(f"Created job: {job.name} (ID: {job.id})")
            return job.to_dict(), 201
            
        except InvalidJobConfigurationError as e:
            logger.warning(f"Invalid job configuration: {str(e)}")
            jobs_ns.abort(400, message=str(e))
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")

@jobs_ns.route('/<string:job_id>')
@jobs_ns.param('job_id', 'The job identifier')
class JobResource(Resource):
    """Individual job resource"""
    
    @jobs_ns.doc('get_job')
    @jobs_ns.marshal_with(job_response_model)
    @jobs_ns.response(200, 'Success')
    @jobs_ns.response(404, 'Job not found', error_model)
    def get(self, job_id):
        """
        Get job details by ID
        
        Returns detailed information about a specific job
        """
        try:
            job = job_service.get_job_by_id(job_id)
            return job.to_dict(include_sensitive=True), 200
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")
    
    @jobs_ns.doc('update_job')
    @jobs_ns.expect(update_job_model, validate=True)
    @jobs_ns.marshal_with(job_response_model)
    @jobs_ns.response(200, 'Job updated successfully')
    @jobs_ns.response(404, 'Job not found', error_model)
    @jobs_ns.response(400, 'Invalid job configuration', error_model)
    def put(self, job_id):
        """
        Update job configuration
        
        Updates an existing job with new configuration
        """
        try:
            updates = request.get_json()
            job = job_service.update_job(job_id, updates)
            
            logger.info(f"Updated job: {job.name} (ID: {job.id})")
            return job.to_dict(), 200
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except InvalidJobConfigurationError as e:
            jobs_ns.abort(400, message=str(e))
        except Exception as e:
            logger.error(f"Error updating job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")
    
    @jobs_ns.doc('delete_job')
    @jobs_ns.response(204, 'Job deleted successfully')
    @jobs_ns.response(404, 'Job not found', error_model)
    def delete(self, job_id):
        """
        Delete a job
        
        Permanently deletes a job and removes it from the scheduler
        """
        try:
            job_service.delete_job(job_id)
            logger.info(f"Deleted job: {job_id}")
            return None, 204
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error deleting job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")

@jobs_ns.route('/<string:job_id>/pause')
@jobs_ns.param('job_id', 'The job identifier')
class JobPauseResource(Resource):
    """Job pause/resume operations"""
    
    @jobs_ns.doc('pause_job')
    @jobs_ns.marshal_with(job_response_model)
    @jobs_ns.response(200, 'Job paused successfully')
    @jobs_ns.response(404, 'Job not found', error_model)
    def post(self, job_id):
        """
        Pause job execution
        
        Temporarily pauses a job and removes it from the scheduler
        """
        try:
            job = job_service.pause_job(job_id)
            logger.info(f"Paused job: {job.name} (ID: {job.id})")
            return job.to_dict(), 200
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")

@jobs_ns.route('/<string:job_id>/resume')
@jobs_ns.param('job_id', 'The job identifier')
class JobResumeResource(Resource):
    """Job resume operations"""
    
    @jobs_ns.doc('resume_job')
    @jobs_ns.marshal_with(job_response_model)
    @jobs_ns.response(200, 'Job resumed successfully')
    @jobs_ns.response(404, 'Job not found', error_model)
    def post(self, job_id):
        """
        Resume job execution
        
        Resumes a paused job and adds it back to the scheduler
        """
        try:
            job = job_service.resume_job(job_id)
            logger.info(f"Resumed job: {job.name} (ID: {job.id})")
            return job.to_dict(), 200
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")

@jobs_ns.route('/<string:job_id>/executions')
@jobs_ns.param('job_id', 'The job identifier')
class JobExecutionsResource(Resource):
    """Job execution history"""
    
    @jobs_ns.doc('get_job_executions')
    @jobs_ns.expect(jobs_ns.parser()
        .add_argument('page', type=int, default=1, help='Page number')
        .add_argument('per_page', type=int, default=20, help='Items per page')
    )
    @jobs_ns.marshal_with(executions_list_response_model)
    @jobs_ns.response(200, 'Success')
    @jobs_ns.response(404, 'Job not found', error_model)
    def get(self, job_id):
        """
        Get job execution history
        
        Returns paginated list of job executions with details
        """
        try:
            # Get pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            
            # Validate pagination
            page, per_page = validate_pagination(page, per_page)
            
            # Get executions
            result = job_service.get_job_executions(
                job_id=job_id,
                page=page,
                per_page=per_page
            )
            
            return result, 200
            
        except JobNotFoundError as e:
            jobs_ns.abort(404, message=str(e))
        except Exception as e:
            logger.error(f"Error getting executions for job {job_id}: {str(e)}")
            jobs_ns.abort(500, message="Internal server error")
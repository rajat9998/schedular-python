"""
Global error handlers for the Flask application
Provides consistent error responses across the API
"""
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from src.common.exceptions import (
    SchedulerError, JobNotFoundError, InvalidJobConfigurationError,
    ValidationError, RateLimitExceededError
)

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Register global error handlers with the Flask app"""
    
    @app.errorhandler(JobNotFoundError)
    def handle_job_not_found(error):
        """Handle job not found errors"""
        response = {
            'error': {
                'message': error.message,
                'code': 'JOB_NOT_FOUND',
                'type': 'JobNotFoundError'
            }
        }
        return jsonify(response), 404
    
    @app.errorhandler(InvalidJobConfigurationError)
    def handle_invalid_job_config(error):
        """Handle invalid job configuration errors"""
        response = {
            'error': {
                'message': error.message,
                'code': 'INVALID_CONFIGURATION',
                'type': 'InvalidJobConfigurationError'
            }
        }
        return jsonify(response), 400
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors"""
        response = {
            'error': {
                'message': error.message,
                'code': 'VALIDATION_ERROR',
                'type': 'ValidationError'
            }
        }
        if error.field:
            response['error']['field'] = error.field
        
        return jsonify(response), 422
    
    @app.errorhandler(RateLimitExceededError)
    def handle_rate_limit_error(error):
        """Handle rate limiting errors"""
        response = {
            'error': {
                'message': error.message,
                'code': 'RATE_LIMIT_EXCEEDED',
                'type': 'RateLimitExceededError'
            }
        }
        if error.retry_after:
            response['error']['retry_after'] = error.retry_after
        
        return jsonify(response), 429
    
    @app.errorhandler(SchedulerError)
    def handle_scheduler_error(error):
        """Handle general scheduler errors"""
        logger.error(f"Scheduler error: {str(error)}")
        response = {
            'error': {
                'message': str(error),
                'code': 'SCHEDULER_ERROR',
                'type': 'SchedulerError'
            }
        }
        return jsonify(response), 500
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        """Handle database errors"""
        logger.error(f"Database error: {str(error)}")
        response = {
            'error': {
                'message': 'Database operation failed',
                'code': 'DATABASE_ERROR',
                'type': 'SQLAlchemyError'
            }
        }
        return jsonify(response), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions"""
        response = {
            'error': {
                'message': error.description,
                'code': error.name.upper().replace(' ', '_'),
                'type': 'HTTPException'
            }
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors"""
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        response = {
            'error': {
                'message': 'An unexpected error occurred',
                'code': 'INTERNAL_SERVER_ERROR',
                'type': 'Exception'
            }
        }
        # Don't expose internal error details in production
        if app.debug:
            response['error']['details'] = str(error)
        
        return jsonify(response), 500
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        response = {
            'error': {
                'message': 'Resource not found',
                'code': 'NOT_FOUND',
                'type': 'NotFound'
            }
        }
        return jsonify(response), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle method not allowed errors"""
        response = {
            'error': {
                'message': 'Method not allowed for this endpoint',
                'code': 'METHOD_NOT_ALLOWED',
                'type': 'MethodNotAllowed'
            }
        }
        return jsonify(response), 405
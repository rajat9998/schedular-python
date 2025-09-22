#!/usr/bin/env python3
"""
Scheduler Microservice
A production-ready job scheduling service with Flask
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api
import logging
from logging.handlers import RotatingFileHandler

from src.common.config import Config
from src.common.extensions import db, migrate

sys.path.insert(0, 'src/')

def create_app(config_class=Config):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize API with Swagger documentation
    api = Api(
        app,
        version='1.0',
        title='Job Scheduler Microservice',
        description='A scalable job scheduling service',
        doc='/docs/',
        prefix='/api/v1'
    )
    
    # Register blueprints/namespaces
    from src.routes.jobs import jobs_ns
    api.add_namespace(jobs_ns, path='/jobs')
    
    # Register error handlers
    from src.common.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Setup logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/scheduler.log', maxBytes=10240, backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Scheduler microservice startup')
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5050)
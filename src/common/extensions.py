"""
Flask extensions initialization
Following the application factory pattern
"""
import redis
import atexit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# Database
db = SQLAlchemy()
migrate = Migrate()

# Redis connection
redis_client = None

def init_redis(app):
    """Initialize Redis connection"""
    global redis_client
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    redis_client = redis.from_url(redis_url, decode_responses=True)
    return redis_client

# APScheduler configuration
def init_scheduler(app):
    """Initialize APScheduler with Redis backend"""
    jobstores = {
        'default': RedisJobStore(
            host='localhost', 
            port=6379, 
            db=2,
            decode_responses=True
        )
    }
    
    executors = {
        'default': ThreadPoolExecutor(20),
    }
    
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='UTC'
    )
    
    scheduler.start()
    
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    
    return scheduler
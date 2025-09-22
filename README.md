# Job Scheduler Microservice

A production-ready, scalable job scheduling microservice built with Flask, PostgreSQL, Redis, and APScheduler. This service provides comprehensive job management capabilities with RESTful APIs, supporting various job types including email notifications, data processing, report generation, cleanup tasks, and custom jobs.

## 🚀 Features

- **Flexible Job Scheduling**: Support for both cron expressions and interval-based scheduling
- **Multiple Job Types**: Email notifications, data processing, report generation, cleanup tasks, backup tasks, and custom jobs
- **Comprehensive APIs**: Full CRUD operations with detailed job management
- **Execution Tracking**: Complete execution history with performance metrics
- **Retry Logic**: Configurable retry mechanisms with exponential backoff
- **Production Ready**: Docker containerization, health checks, and monitoring
- **Scalable Architecture**: Designed to handle 10,000+ users and 6,000+ API requests per minute
- **API Documentation**: Auto-generated Swagger/OpenAPI documentation
- **SOLID Principles**: Clean, maintainable code following best practices

## 📋 Table of Contents

- [Architecture](#architecture)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)
- [Job Types](#job-types)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Development](#development)
- [Testing](#testing)
- [Monitoring](#monitoring)
- [Scaling Strategy](#scaling-strategy)

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Flask API     │    │   PostgreSQL     │    │     Redis       │
│   (REST APIs)   │◄───┤   (Job Storage)  │    │ (Job Queue)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                               ▲
         ▼                                               │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Job Service    │    │   APScheduler    │    │ Job Executor    │
│ (Business Logic)│◄───┤  (Scheduling)    │◄───┤ (Job Execution) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Design Principles

- **SOLID Principles**: Each component has a single responsibility
- **Dependency Injection**: Loose coupling between components
- **Repository Pattern**: Clean data access layer
- **Factory Pattern**: Application creation and configuration
- **Observer Pattern**: Event-driven job execution

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Quick Start with Docker

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd job-scheduler-microservice
   ```

2. **Start all services**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Initialize the database**:
   ```bash
   docker-compose exec scheduler-api flask db init
   docker-compose exec scheduler-api flask db migrate -m "Initial migration"
   docker-compose exec scheduler-api flask db upgrade
   ```

4. **Access the services**:
   - API Base URL: http://localhost/api/v1
   - API Documentation: http://localhost/docs/
   - Health Check: http://localhost/health

### Manual Installation

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export FLASK_ENV=development
   export DATABASE_URL=postgresql://scheduler_user:scheduler_pass@localhost/scheduler_db
   export REDIS_URL=redis://localhost:6379/0
   export SECRET_KEY=your-secret-key-here
   ```

4. **Initialize database**:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. **Start Redis**:
   ```bash
   redis-server
   ```

6. **Run the application**:
   ```bash
   python app.py
   ```

## 📡 API Endpoints

### Jobs Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobs` | List all jobs with filtering and pagination |
| POST | `/api/v1/jobs` | Create a new job |
| GET | `/api/v1/jobs/{id}` | Get job details by ID |
| PUT | `/api/v1/jobs/{id}` | Update job configuration |
| DELETE | `/api/v1/jobs/{id}` | Delete a job |
| POST | `/api/v1/jobs/{id}/pause` | Pause job execution |
| POST | `/api/v1/jobs/{id}/resume` | Resume job execution |
| GET | `/api/v1/jobs/{id}/executions` | Get job execution history |

### Example Usage

**Create a Job**:
```bash
curl -X POST http://localhost/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly Report Generation",
    "description": "Generate weekly sales report every Monday",
    "job_type": "report_generation",
    "cron_expression": "0 9 * * 1",
    "job_data": {
      "report_type": "sales",
      "format": "pdf",
      "recipients": ["manager@company.com"]
    },
    "timeout_seconds": 1800,
    "max_retries": 3,
    "priority": 7
  }'
```

**List Jobs with Filtering**:
```bash
curl "http://localhost/api/v1/jobs?status=pending&job_type=email_notification&page=1&per_page=20"
```

**Get Job Details**:
```bash
curl http://localhost/api/v1/jobs/{job-id}
```

**Pause a Job**:
```bash
curl -X POST http://localhost/api/v1/jobs/{job-id}/pause
```

**Get Execution History**:
```bash
curl "http://localhost/api/v1/jobs/{job-id}/executions?page=1&per_page=10"
```

## 🔧 Job Types

The service supports multiple built-in job types with POC execution logic:

### 1. Email Notification
```json
{
  "job_type": "email_notification",
  "job_data": {
    "recipient": "user@company.com",
    "subject": "Weekly Report Ready",
    "body": "Your weekly report has been generated and is ready for review."
  }
}
```

### 2. Data Processing
```json
{
  "job_type": "data_processing",
  "job_data": {
    "dataset": "sales_data",
    "operation": "aggregate",
    "parameters": {
      "record_count": 5000,
      "aggregation_type": "sum"
    }
  }
}
```

### 3. Report Generation
```json
{
  "job_type": "report_generation",
  "job_data": {
    "report_type": "financial",
    "date_range": "last_month",
    "format": "pdf",
    "template": "monthly_summary"
  }
}
```

### 4. Cleanup Task
```json
{
  "job_type": "cleanup_task",
  "job_data": {
    "cleanup_type": "temp_files",
    "retention_days": 7,
    "path": "/tmp/application_cache"
  }
}
```

### 5. Backup Task
```json
{
  "job_type": "backup_task",
  "job_data": {
    "backup_type": "database",
    "destination": "s3://backups/db/",
    "compression": true,
    "encryption": true
  }
}
```

### 6. Custom Job
```json
{
  "job_type": "custom",
  "job_data": {
    "operation": "data_migration",
    "parameters": {
      "source": "legacy_db",
      "destination": "new_db",
      "batch_size": 1000
    }
  }
}
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode (development/production) | `development` |
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///scheduler.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | Flask secret key | Required |
| `LOG_LEVEL` | Logging level | `INFO` |
| `JOBS_PER_PAGE` | Default pagination size | `20` |
| `MAX_JOBS_PER_USER` | Maximum jobs per user | `100` |

### Scheduling Configuration

**Cron Expressions**:
- `0 9 * * 1` - Every Monday at 9:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 1 * *` - First day of every month
- `*/30 * * * *` - Every 30 minutes

**Interval Scheduling**:
- `3600` - Every hour (3600 seconds)
- `86400` - Daily (86400 seconds)
- `604800` - Weekly (604800 seconds)

### Database Configuration

For production, use PostgreSQL with the following optimizations:
```yaml
postgresql.conf:
  shared_buffers: 256MB
  effective_cache_size: 1GB
  work_mem: 4MB
  maintenance_work_mem: 64MB
  checkpoint_completion_target: 0.7
```

## 🚀 Deployment

### Production Docker Deployment

1. **Build the image**:
   ```bash
   docker build -t scheduler-microservice:latest .
   ```

2. **Run with production settings**:
   ```bash
   docker run -d \
     --name scheduler-api \
     -p 5000:5000 \
     -e FLASK_ENV=production \
     -e DATABASE_URL=postgresql://user:pass@db:5432/scheduler \
     -e REDIS_URL=redis://redis:6379/0 \
     scheduler-microservice:latest
   ```


### Health Checks

The service includes comprehensive health checks:
- **Application health**: `/health`
- **Database connectivity**: Automatic connection testing
- **Redis connectivity**: Queue status verification
- **Scheduler status**: Active jobs monitoring

## 💻 Development

### Project Structure

```
job-scheduler-microservice/
├── src/
│   ├── models/
│   │   └── job.py                 # Job and JobExecution models
│   ├── services/
│   │   ├── jobs.py                # Business logic layer
│   │   ├── scheduler.py           # APScheduler management
│   │   └── executor.py            # Job execution logic
│   ├── routes/
│   │   └── jobs.py               # REST API endpoints
│   └── common/
|       ├── config.py             # Configuration management
|       ├── extensions.py         # Flask extensions
│       ├── exceptions.py         # Custom exceptions
│       ├── validators.py         # Input validation
│       └── error_handlers.py     # Global error handling
├── migrations/                   # Database migrations
├── main.py                       # Application factory
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Development environment
├── README.md                    # This file
```

### Adding New Job Types

1. **Add job type enum** in `models/job.py`:
   ```python
   class JobType(Enum):
       YOUR_NEW_TYPE = "your_new_type"
   ```

2. **Implement job handler** in `services/job_executor.py`:
   ```python
   def _handle_your_new_type(self, job: Job) -> str:
       job_data = self._parse_job_data(job.job_data)
       # Your job logic here
       return "Job completed successfully"
   ```

3. **Register handler** in `JobExecutor.__init__()`:
   ```python
   self.job_handlers[JobType.YOUR_NEW_TYPE] = self._handle_your_new_type
   ```

### Code Quality Standards

- **PEP 8**: Python code style guide
- **Type Hints**: Full type annotation coverage
- **Docstrings**: Google-style docstrings
- **Error Handling**: Comprehensive exception handling
- **Logging**: Structured logging with correlation IDs
- **Testing**: Unit and integration tests

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-flask pytest-cov factory-boy

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run with markers
pytest -m "not slow" -v
```

### Test Structure

```
tests/
├── unit/
│   ├── test_models.py           # Model tests
│   ├── test_services.py         # Service layer tests
│   ├── test_validators.py       # Validation tests
│   └── test_job_executor.py     # Job execution tests
├── integration/
│   ├── test_api_endpoints.py    # API integration tests
│   └── test_job_scheduling.py   # End-to-end scheduling tests
├── fixtures/
│   └── job_fixtures.py          # Test data factories
└── conftest.py                  # Test configuration
```

### Example Test

```python
def test_create_job_with_cron_expression(client, db):
    """Test job creation with cron scheduling"""
    job_data = {
        "name": "Test Cron Job",
        "job_type": "email_notification",
        "cron_expression": "0 9 * * 1",
        "job_data": {"recipient": "test@example.com"}
    }
    
    response = client.post('/api/v1/jobs', json=job_data)
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == "Test Cron Job"
    assert data['cron_expression'] == "0 9 * * 1"
    assert data['next_run_time'] is not None
```

## 📊 Monitoring

### Metrics to Monitor

**Application Metrics**:
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx responses)
- Active jobs count
- Job execution success rate
- Average job execution time

**System Metrics**:
- CPU utilization
- Memory usage
- Database connections
- Redis memory usage
- Disk I/O operations

**Business Metrics**:
- Jobs created per hour
- Jobs completed successfully
- Failed jobs requiring attention
- Most popular job types
- User activity patterns

### Logging

The service implements structured logging:

```python
import logging
logger = logging.getLogger(__name__)

logger.info(
    "Job executed successfully",
    extra={
        "job_id": job.id,
        "job_name": job.name,
        "duration": execution_time,
        "status": "completed"
    }
)
```

### Health Check Endpoint

```bash
curl http://localhost/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "scheduler": "ok"
  }
}
```

## 📈 Scaling Strategy

For detailed scaling information, see [SCALING_STRATEGY.md](SCALING_STRATEGY.md) which covers:

- **Multi-service architecture** decomposition
- **Geographic distribution** strategies
- **Database scaling** with read replicas
- **API management** and rate limiting
- **Caching strategies** (multi-level)
- **Performance optimization** techniques
- **Monitoring and alerting** setup

### Key Scaling Points

**Current Capacity**: Single instance handles ~50 RPS
**Target Capacity**: 100 RPS (6,000 requests/minute)
**Scaling Approach**: 
- 3-5 API service instances
- Database read replicas
- Redis clustering
- Load balancing with Nginx

## 🛡️ Security

- **Input Validation**: All inputs validated and sanitized
- **SQL Injection Protection**: ORM-based database access
- **Authentication**: API key and JWT token support
- **Rate Limiting**: Per-IP and per-user rate limits
- **HTTPS**: SSL/TLS encryption in production
- **Security Headers**: Standard security headers applied

---

Built with ❤️ using Flask, PostgreSQL, Redis, and APScheduler
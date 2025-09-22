# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r scheduler && useradd --no-log-init -r -g scheduler scheduler

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set work directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/scheduler/.local

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs && \
    chown -R scheduler:scheduler /app

# Switch to non-root user
USER scheduler

# Set Python path
ENV PATH=/home/scheduler/.local/bin:$PATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5050/api/v1/jobs?page=1&per_page=1 || exit 1

# Default command
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "4", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "120", "--keep-alive", "5", "main:create_app()"]
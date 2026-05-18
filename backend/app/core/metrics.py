"""Prometheus metrics for monitoring."""

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.core import CollectorRegistry

# Create a custom registry
registry = CollectorRegistry()

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=registry,
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    registry=registry,
)

# Celery task metrics
celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks",
    ["task_name", "status"],
    registry=registry,
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task duration in seconds",
    ["task_name"],
    registry=registry,
)

celery_tasks_active = Gauge(
    "celery_tasks_active",
    "Number of active Celery tasks",
    registry=registry,
)

# File processing metrics
files_processed_total = Counter(
    "files_processed_total",
    "Total files processed",
    ["file_type", "platform", "status"],
    registry=registry,
)

file_processing_duration_seconds = Histogram(
    "file_processing_duration_seconds",
    "File processing duration in seconds",
    ["file_type", "platform"],
    registry=registry,
)

file_size_bytes = Histogram(
    "file_size_bytes",
    "File size in bytes",
    ["file_type"],
    registry=registry,
)

# Business metrics
upload_files_total = Counter(
    "upload_files_total",
    "Total uploaded files",
    ["org_id", "platform"],
    registry=registry,
)

summary_records_total = Gauge(
    "summary_records_total",
    "Total summary records",
    ["org_id"],
    registry=registry,
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total errors",
    ["error_type", "module"],
    registry=registry,
)


def get_metrics():
    """Get current metrics in Prometheus format."""
    return generate_latest(registry)

FROM python:3.13-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --only main

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY prometheus_todoist_exporter/ /app/prometheus_todoist_exporter/

# Set environment variables
ENV EXPORTER_PORT=9090
ENV METRICS_PATH="/metrics"
ENV COLLECTION_INTERVAL=60

# Expose the port
EXPOSE 9090

# Run the exporter
CMD ["python", "-m", "prometheus_todoist_exporter"]

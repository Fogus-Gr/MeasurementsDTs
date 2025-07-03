#/MeasurementsDTs/dev_tools/Dockerfile

# Use a slim Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install necessary Python packages
RUN pip install --no-cache-dir flask opencv-python-headless gunicorn

# Copy only the application file
COPY app.py .

# Expose Flask default port
EXPOSE 8089

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Healthcheck to monitor the application
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8089/ || exit 1

# Run the application
CMD gunicorn --bind 0.0.0.0:${PORT:-8089} --timeout 3600 --workers 1 --threads 4 --worker-class gthread app:app

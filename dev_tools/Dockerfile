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
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:${PORT:-5000}", "app:app"]

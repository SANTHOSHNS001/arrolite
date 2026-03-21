# Use the official Python image
FROM python:3.11-slim

# Set environment variables (Updated to avoid legacy warnings)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# 1. Install system dependencies for mysqlclient
# We combine these into one RUN command to keep the image size small
RUN apt-get update && apt-get install -y \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of the project code
COPY . .

# Expose the port (good practice for documentation)
EXPOSE 8000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "arrolite.wsgi:application"]
# Use an official Python runtime as base image
# Using slim variant for smaller image size
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Set environment variables
# - Prevents Python from writing .pyc files
# - Ensures Python output is sent straight to terminal without buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
# We keep this minimal for smaller image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files into the working directory
COPY . .

# Expose the port the app runs on
EXPOSE 7860

# Command to run the application
# Using Uvicorn with WSGI interface for Flask
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--interface", "wsgi"]

# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
build-essential \
default-libmysqlclient-dev \
pkg-config \
libssl-dev \
libffi-dev \
libmariadb-dev-compat \
libmariadb-dev \
libpq-dev \
git \
iputils-ping \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir --force-reinstall --exists-action w -r requirements.txt

# Install Uvicorn
RUN pip install uvicorn

# Create the log directory
RUN mkdir -p /app/logs && chown -R www-data:www-data /app/logs && chmod -R 755 /app/logs

# Expose the port that Uvicorn will run on
EXPOSE 8000

# Command to run the application using Uvicorn
CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput  && uvicorn project.asgi:application --host 0.0.0.0 --port 8000"]